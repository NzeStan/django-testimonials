"""
Celery tasks for the testimonials app.
These tasks handle background processing for emails, media, and other heavy operations.
"""

import logging
from typing import Dict, Any
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .conf import app_settings
from .utils import generate_thumbnails, log_testimonial_action, invalidate_testimonial_cache

logger = logging.getLogger("testimonials")

# Try to import Celery components
try:
    from celery import shared_task
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Define a dummy decorator for when Celery is not available
    def shared_task(func):
        return func


# === EMAIL TASKS ===

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_testimonial_notification_email(self, testimonial_id: str, email_type: str, 
                                       recipient_email: str, context_data: Dict[str, Any] = None):
    """
    Send testimonial-related notification emails.
    
    Args:
        testimonial_id: ID of the testimonial
        email_type: Type of email (approved, rejected, response, new)
        recipient_email: Email address to send to
        context_data: Additional context for email template
    """
    try:
        from .models import Testimonial
        
        testimonial = Testimonial.objects.select_related('category', 'author').get(id=testimonial_id)
        
        # Default context
        context = {
            'testimonial': testimonial,
            'site_name': getattr(settings, 'SITE_NAME', 'Django Testimonials'),
            'site_url': getattr(settings, 'SITE_URL', ''),
        }
        
        # Add custom context data
        if context_data:
            context.update(context_data)
        
        # Email templates mapping
        templates = {
            'approved': {
                'subject': 'testimonials/emails/testimonial_approved_subject.txt',
                'body': 'testimonials/emails/testimonial_approved_body.txt',
            },
            'rejected': {
                'subject': 'testimonials/emails/testimonial_rejected_subject.txt',
                'body': 'testimonials/emails/testimonial_rejected_body.txt',
            },
            'response': {
                'subject': 'testimonials/emails/testimonial_response_subject.txt',
                'body': 'testimonials/emails/testimonial_response_body.txt',
            },
            'new': {
                'subject': 'testimonials/emails/new_testimonial_subject.txt',
                'body': 'testimonials/emails/new_testimonial_body.txt',
            }
        }
        
        if email_type not in templates:
            raise ValueError(f"Unknown email type: {email_type}")
        
        template_config = templates[email_type]
        
        # Render email content
        subject = render_to_string(template_config['subject'], context).strip()
        message = render_to_string(template_config['body'], context)
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        log_testimonial_action(
            testimonial, 
            f"email_sent_{email_type}", 
            extra_data={
                'recipient_email': recipient_email,
                'email_type': email_type
            }
        )
        
        logger.info(f"Successfully sent {email_type} email for testimonial {testimonial_id}")
        
    except Exception as exc:
        logger.error(f"Failed to send {email_type} email for testimonial {testimonial_id}: {exc}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            # Log final failure
            logger.error(f"Final failure sending {email_type} email for testimonial {testimonial_id}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_admin_notification_email(self, testimonial_id: str, notification_type: str):
    """
    Send notification emails to administrators.
    
    Args:
        testimonial_id: ID of the testimonial
        notification_type: Type of notification (new_testimonial, urgent_review, etc.)
    """
    try:
        from .models import Testimonial
        
        if not app_settings.NOTIFICATION_EMAIL:
            logger.info("Admin notifications disabled - no notification email configured")
            return
        
        testimonial = Testimonial.objects.select_related('category', 'author').get(id=testimonial_id)
        
        context = {
            'testimonial': testimonial,
            'site_name': getattr(settings, 'SITE_NAME', 'Django Testimonials'),
            'site_url': getattr(settings, 'SITE_URL', ''),
            'admin_url': f"{getattr(settings, 'SITE_URL', '')}/admin/testimonials/testimonial/{testimonial_id}/change/"
        }
        
        if notification_type == 'new_testimonial':
            subject = f"New testimonial received - {context['site_name']}"
            message = f"""
A new testimonial has been submitted and requires your attention:

Author: {testimonial.author_name}
Company: {testimonial.company or 'Not specified'}
Rating: {testimonial.rating}/5
Content: {testimonial.content[:200]}{'...' if len(testimonial.content) > 200 else ''}

Status: {testimonial.get_status_display()}
Category: {testimonial.category.name if testimonial.category else 'Uncategorized'}

Review it here: {context['admin_url']}

Best regards,
{context['site_name']} System
            """
        else:
            logger.warning(f"Unknown admin notification type: {notification_type}")
            return
        
        # Send to admin email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[app_settings.NOTIFICATION_EMAIL],
            fail_silently=False,
        )
        
        logger.info(f"Successfully sent admin notification for testimonial {testimonial_id}")
        
    except Exception as exc:
        logger.error(f"Failed to send admin notification for testimonial {testimonial_id}: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# === MEDIA PROCESSING TASKS ===

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_testimonial_media(self, media_id: str):
    """
    Process uploaded testimonial media (thumbnails, validation, etc.).
    
    Args:
        media_id: ID of the testimonial media
    """
    try:
        from .models import TestimonialMedia
        from .constants import TestimonialMediaType
        
        media = TestimonialMedia.objects.select_related('testimonial').get(id=media_id)
        
        # Process based on media type
        if media.media_type == TestimonialMediaType.IMAGE:
            # Generate thumbnails
            thumbnails = generate_thumbnails(media.file)
            
            if thumbnails:
                # Store thumbnail information in extra_data
                if not hasattr(media, 'extra_data') or not media.extra_data:
                    media.extra_data = {}
                
                media.extra_data['thumbnails'] = {}
                
                for size_name, thumbnail_file in thumbnails.items():
                    # Save thumbnail file
                    thumbnail_path = f"thumbnails/{size_name}_{media.file.name}"
                    
                    # Store thumbnail info
                    media.extra_data['thumbnails'][size_name] = {
                        'path': thumbnail_path,
                        'generated_at': timezone.now().isoformat()
                    }
                
                media.save(update_fields=['extra_data'])
                
                logger.info(f"Generated {len(thumbnails)} thumbnails for media {media_id}")
        
        elif media.media_type == TestimonialMediaType.VIDEO:
            # Video processing (basic validation for now)
            # In a full implementation, you might extract video metadata,
            # generate preview frames, etc.
            logger.info(f"Video media {media_id} processed (validation only)")
        
        elif media.media_type == TestimonialMediaType.AUDIO:
            # Audio processing (basic validation for now)
            logger.info(f"Audio media {media_id} processed (validation only)")
        
        # Log the processing
        log_testimonial_action(
            media.testimonial,
            "media_processed",
            extra_data={
                'media_id': str(media_id),
                'media_type': media.media_type
            }
        )
        
        # Invalidate related cache
        invalidate_testimonial_cache(
            testimonial_id=media.testimonial_id
        )
        
    except Exception as exc:
        logger.error(f"Failed to process media {media_id}: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# === BULK OPERATION TASKS ===

@shared_task(bind=True, max_retries=2)
def bulk_moderate_testimonials(self, testimonial_ids: list, action: str, 
                              user_id: int = None, extra_data: Dict[str, Any] = None):
    """
    Perform bulk moderation actions on testimonials.
    FIXED: Added verify and unverify actions.
    """
    try:
        from .models import Testimonial
        from .constants import TestimonialStatus
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.get(id=user_id) if user_id else None
        
        # Process in batches for better performance
        batch_size = app_settings.BULK_OPERATION_BATCH_SIZE
        processed_count = 0
        
        for i in range(0, len(testimonial_ids), batch_size):
            batch_ids = testimonial_ids[i:i + batch_size]
            testimonials = Testimonial.objects.filter(id__in=batch_ids)
            
            for testimonial in testimonials:
                if action == 'approve':
                    testimonial.status = TestimonialStatus.APPROVED
                    testimonial.approved_at = timezone.now()
                    testimonial.approved_by = user
                    
                elif action == 'reject':
                    testimonial.status = TestimonialStatus.REJECTED
                    if extra_data and 'rejection_reason' in extra_data:
                        testimonial.rejection_reason = extra_data['rejection_reason']
                    
                elif action == 'feature':
                    testimonial.status = TestimonialStatus.FEATURED
                    
                elif action == 'archive':
                    testimonial.status = TestimonialStatus.ARCHIVED
                
                # FIXED: Added verify and unverify
                elif action == 'verify':
                    testimonial.is_verified = True
                    
                elif action == 'unverify':
                    testimonial.is_verified = False
                
                testimonial.save()
                processed_count += 1
                
                # Log individual action
                log_testimonial_action(testimonial, f"bulk_{action}", user)
        
        # Invalidate cache after bulk operation
        invalidate_testimonial_cache()
        
        logger.info(f"Bulk {action} completed: {processed_count} testimonials processed")
        return processed_count
        
    except Exception as exc:
        logger.error(f"Bulk moderation failed for action {action}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)


# === MAINTENANCE TASKS ===

@shared_task
def cleanup_expired_cache():
    """
    Clean up expired cache entries and perform cache maintenance.
    """
    try:
        if not app_settings.USE_REDIS_CACHE:
            logger.info("Redis cache not enabled, skipping cleanup")
            return
        
        from django.core.cache import cache
        
        # Clear any manually managed cache patterns
        # This is a placeholder - actual implementation depends on cache backend
        logger.info("Cache cleanup completed")
        
    except Exception as exc:
        logger.error(f"Cache cleanup failed: {exc}")


@shared_task
def generate_testimonial_stats():
    """
    Generate and cache testimonial statistics.
    This can be run periodically to keep stats fresh.
    """
    try:
        from .models import Testimonial
        from .utils import get_cache_key, cache_get_or_set
        
        def compute_stats():
            return Testimonial.objects.get_stats()
        
        # Generate and cache stats
        cache_key = get_cache_key('stats')
        stats = cache_get_or_set(
            cache_key, 
            compute_stats, 
            timeout=app_settings.CACHE_TIMEOUT * 2  # Cache stats longer
        )
        
        logger.info(f"Generated testimonial stats: {stats['total']} total testimonials")
        return stats
        
    except Exception as exc:
        logger.error(f"Stats generation failed: {exc}")


@shared_task
def optimize_database():
    """
    Perform database optimization tasks.
    """
    try:
        from django.db import connection
        
        # This is a placeholder for database optimization tasks
        # Actual implementation would depend on your database backend
        
        with connection.cursor() as cursor:
            # Example: Update table statistics (PostgreSQL)
            if connection.vendor == 'postgresql':
                cursor.execute("ANALYZE testimonials_testimonial;")
                cursor.execute("ANALYZE testimonials_testimonialcategory;")
                cursor.execute("ANALYZE testimonials_testimonialmedia;")
        
        logger.info("Database optimization completed")
        
    except Exception as exc:
        logger.error(f"Database optimization failed: {exc}")


# === PERIODIC TASK SCHEDULE ===

# Define periodic tasks (these need to be added to CELERY_BEAT_SCHEDULE in settings)
PERIODIC_TASKS = {
    'cleanup-expired-cache': {
        'task': 'testimonials.tasks.cleanup_expired_cache',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'generate-testimonial-stats': {
        'task': 'testimonials.tasks.generate_testimonial_stats',
        'schedule': crontab(minute=0, hour='*/1'),  # Every hour
    },
    'optimize-database': {
        'task': 'testimonials.tasks.optimize_database',
        'schedule': crontab(minute=0, hour=3),  # Daily at 3 AM
    },
}


# === TASK WRAPPER FUNCTIONS ===

def send_testimonial_email(testimonial_id: str, email_type: str, 
                          recipient_email: str, context_data: Dict[str, Any] = None):
    """
    Wrapper function to send testimonial emails (async if Celery enabled, sync otherwise).
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return send_testimonial_notification_email.delay(
            testimonial_id, email_type, recipient_email, context_data
        )
    else:
        return send_testimonial_notification_email(
            testimonial_id, email_type, recipient_email, context_data
        )


def send_admin_notification(testimonial_id: str, notification_type: str):
    """
    Wrapper function to send admin notifications.
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return send_admin_notification_email.delay(testimonial_id, notification_type)
    else:
        return send_admin_notification_email(testimonial_id, notification_type)


def process_media(media_id: str):
    """
    Wrapper function to process media files.
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return process_testimonial_media.delay(media_id)
    else:
        return process_testimonial_media(media_id)


def bulk_moderate(testimonial_ids: list, action: str, user_id: int = None, 
                 extra_data: Dict[str, Any] = None):
    """
    Wrapper function for bulk moderation.
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return bulk_moderate_testimonials.delay(testimonial_ids, action, user_id, extra_data)
    else:
        return bulk_moderate_testimonials(testimonial_ids, action, user_id, extra_data)