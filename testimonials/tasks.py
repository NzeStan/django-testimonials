# testimonials/tasks.py (Updated with Email Notification Settings)

"""
Celery tasks for the testimonials app.
These tasks handle background processing for emails, media, and other heavy operations.
"""

import logging
from typing import Dict, Any
from django.core.mail import send_mail, EmailMultiAlternatives
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
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        # Handle both @shared_task and @shared_task() syntax
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


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
    # Check if email notifications are enabled
    if not app_settings.SEND_EMAIL_NOTIFICATIONS:
        logger.info(f"Email notifications disabled. Skipping {email_type} email for testimonial {testimonial_id}")
        return
    
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
        template_extension = '.html' if app_settings.USE_HTML_EMAILS else '.txt'
        
        templates = {
            'approved': {
                'subject': 'testimonials/emails/testimonial_approved_subject.txt',
                'body_text': 'testimonials/emails/testimonial_approved_body.txt',
                'body_html': 'testimonials/emails/testimonial_approved_body.html',
            },
            'rejected': {
                'subject': 'testimonials/emails/testimonial_rejected_subject.txt',
                'body_text': 'testimonials/emails/testimonial_rejected_body.txt',
                'body_html': 'testimonials/emails/testimonial_rejected_body.html',
            },
            'response': {
                'subject': 'testimonials/emails/testimonial_response_subject.txt',
                'body_text': 'testimonials/emails/testimonial_response_body.txt',
                'body_html': 'testimonials/emails/testimonial_response_body.html',
            },
            'new': {
                'subject': 'testimonials/emails/new_testimonial_subject.txt',
                'body_text': 'testimonials/emails/new_testimonial_body.txt',
                'body_html': 'testimonials/emails/new_testimonial_body.html',
            }
        }
        
        if email_type not in templates:
            raise ValueError(f"Unknown email type: {email_type}")
        
        template_config = templates[email_type]
        
        # Render email content
        subject = render_to_string(template_config['subject'], context).strip()
        text_message = render_to_string(template_config['body_text'], context)
        
        # Determine from email
        from_name = app_settings.EMAIL_FROM_NAME
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        from_address = f"{from_name} <{from_email}>"
        
        # Send HTML email if enabled
        if app_settings.USE_HTML_EMAILS:
            try:
                html_message = render_to_string(template_config['body_html'], context)
                
                # Create email with both text and HTML versions
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=from_address,
                    to=[recipient_email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=False)
                
            except Exception as html_error:
                logger.warning(f"Failed to send HTML email, falling back to text: {html_error}")
                # Fallback to text-only email
                send_mail(
                    subject=subject,
                    message=text_message,
                    from_email=from_address,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
        else:
            # Send text-only email
            send_mail(
                subject=subject,
                message=text_message,
                from_email=from_address,
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
    # Check if admin notifications are enabled
    if not app_settings.SEND_ADMIN_NOTIFICATIONS:
        logger.info(f"Admin notifications disabled. Skipping {notification_type} notification for testimonial {testimonial_id}")
        return
    
    try:
        from .models import Testimonial
        
        # Check if admin email is configured
        admin_email = app_settings.NOTIFICATION_EMAIL
        if not admin_email:
            logger.warning(f"No admin notification email configured. Skipping {notification_type} notification.")
            return
        
        testimonial = Testimonial.objects.select_related('category', 'author').get(id=testimonial_id)
        
        # Context for email template
        context = {
            'testimonial': testimonial,
            'site_name': getattr(settings, 'SITE_NAME', 'Django Testimonials'),
            'site_url': getattr(settings, 'SITE_URL', ''),
            'notification_type': notification_type,
        }
        
        # Email templates
        template_extension = '.html' if app_settings.USE_HTML_EMAILS else '.txt'
        
        subject = render_to_string('testimonials/emails/new_testimonial_subject.txt', context).strip()
        text_message = render_to_string('testimonials/emails/new_testimonial_body.txt', context)
        
        # Determine from email
        from_name = app_settings.EMAIL_FROM_NAME
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        from_address = f"{from_name} <{from_email}>"
        
        # Send HTML email if enabled
        if app_settings.USE_HTML_EMAILS:
            try:
                html_message = render_to_string('testimonials/emails/new_testimonial_body.html', context)
                
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=from_address,
                    to=[admin_email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=False)
                
            except Exception as html_error:
                logger.warning(f"Failed to send HTML admin notification, falling back to text: {html_error}")
                send_mail(
                    subject=subject,
                    message=text_message,
                    from_email=from_address,
                    recipient_list=[admin_email],
                    fail_silently=False,
                )
        else:
            send_mail(
                subject=subject,
                message=text_message,
                from_email=from_address,
                recipient_list=[admin_email],
                fail_silently=False,
            )
        
        logger.info(f"Successfully sent {notification_type} admin notification for testimonial {testimonial_id}")
        
    except Exception as exc:
        logger.error(f"Failed to send admin notification for testimonial {testimonial_id}: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# === MEDIA PROCESSING TASKS ===

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_testimonial_media(self, media_id: str):
    """
    Process uploaded testimonial media (generate thumbnails, optimize, etc.).
    
    Args:
        media_id: ID of the media file
    """
    try:
        from .models import TestimonialMedia
        
        media = TestimonialMedia.objects.get(id=media_id)
        
        # Generate thumbnails for images
        if media.media_type == 'image':
            generate_thumbnails(media)
            logger.info(f"Generated thumbnails for media {media_id}")
        
        # Add more media processing logic here (video transcoding, etc.)
        
    except Exception as exc:
        logger.error(f"Failed to process media {media_id}: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# === BULK OPERATIONS TASKS ===

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def bulk_moderate_testimonials(self, testimonial_ids: list, action: str, user_id: int = None, 
                              extra_data: Dict[str, Any] = None):
    """
    Perform bulk moderation actions on testimonials.
    
    Args:
        testimonial_ids: List of testimonial IDs
        action: Action to perform (approve, reject, feature, archive)
        user_id: ID of user performing the action
        extra_data: Additional data (e.g., rejection_reason)
    """
    try:
        from .models import Testimonial
        from .constants import TestimonialStatus
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.get(id=user_id) if user_id else None
        
        testimonials = Testimonial.objects.filter(id__in=testimonial_ids)
        updated_count = 0
        
        for testimonial in testimonials:
            if action == 'approve':
                if testimonial.status != TestimonialStatus.APPROVED:
                    testimonial.status = TestimonialStatus.APPROVED
                    testimonial.save()
                    updated_count += 1
                    
                    # Send approval email if enabled
                    if app_settings.SEND_EMAIL_NOTIFICATIONS and testimonial.author_email:
                        send_testimonial_notification_email.delay(
                            str(testimonial.id),
                            'approved',
                            testimonial.author_email
                        )
            
            elif action == 'reject':
                if testimonial.status != TestimonialStatus.REJECTED:
                    testimonial.status = TestimonialStatus.REJECTED
                    if extra_data and 'rejection_reason' in extra_data:
                        testimonial.rejection_reason = extra_data['rejection_reason']
                    testimonial.save()
                    updated_count += 1
                    
                    # Send rejection email if enabled
                    if app_settings.SEND_EMAIL_NOTIFICATIONS and testimonial.author_email:
                        send_testimonial_notification_email.delay(
                            str(testimonial.id),
                            'rejected',
                            testimonial.author_email
                        )
            
            elif action == 'feature':
                if testimonial.status != TestimonialStatus.FEATURED:
                    testimonial.status = TestimonialStatus.FEATURED
                    testimonial.save()
                    updated_count += 1
            
            elif action == 'archive':
                if testimonial.status != TestimonialStatus.ARCHIVED:
                    testimonial.status = TestimonialStatus.ARCHIVED
                    testimonial.save()
                    updated_count += 1
            
            # Log the action
            log_testimonial_action(
                testimonial,
                f"bulk_{action}",
                user=user,
                extra_data=extra_data
            )
        
        # Invalidate caches
        invalidate_testimonial_cache()
        
        logger.info(f"Bulk {action} completed: {updated_count}/{len(testimonial_ids)} testimonials updated")
        return updated_count
        
    except Exception as exc:
        logger.error(f"Bulk moderation failed: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))


# === CACHE MANAGEMENT TASKS ===

@shared_task
def cleanup_expired_cache():
    """
    Clean up expired cache entries.
    """
    try:
        if app_settings.USE_REDIS_CACHE:
            from django.core.cache import cache
            
            # This is handled automatically by Redis TTL
            # but we can do additional cleanup here if needed
            logger.info("Cache cleanup completed")
        
    except Exception as exc:
        logger.error(f"Cache cleanup failed: {exc}")


@shared_task
def generate_testimonial_stats():
    """
    Generate and cache testimonial statistics.
    """
    try:
        from .models import Testimonial
        from django.core.cache import cache
        from django.db.models import Count, Avg
        
        stats = {
            'total': Testimonial.objects.count(),
            'approved': Testimonial.objects.filter(status='approved').count(),
            'pending': Testimonial.objects.filter(status='pending').count(),
            'rejected': Testimonial.objects.filter(status='rejected').count(),
            'featured': Testimonial.objects.filter(status='featured').count(),
            'average_rating': Testimonial.objects.filter(
                status='approved'
            ).aggregate(Avg('rating'))['rating__avg'] or 0,
            'by_category': list(
                Testimonial.objects.filter(status='approved')
                .values('category__name')
                .annotate(count=Count('id'))
            ),
        }
        
        # Cache the stats
        cache_key = f"{app_settings.CACHE_KEY_PREFIX}_stats"
        cache.set(cache_key, stats, app_settings.CACHE_TIMEOUT)
        
        logger.info("Testimonial statistics generated and cached")
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
# These wrapper functions handle both async (Celery) and sync execution

def send_testimonial_email(testimonial_id: str, email_type: str, 
                          recipient_email: str, context_data: Dict[str, Any] = None):
    """
    Wrapper function to send testimonial emails (async if Celery enabled, sync otherwise).
    
    Args:
        testimonial_id: ID of the testimonial
        email_type: Type of email (approved, rejected, response)
        recipient_email: Recipient email address
        context_data: Optional context data for email template
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        # Async execution via Celery
        return send_testimonial_notification_email.delay(
            testimonial_id, email_type, recipient_email, context_data
        )
    else:
        # Synchronous execution - call the actual task function directly
        # When bind=True, we need to pass a mock self object
        class MockRequest:
            retries = 0
        
        class MockSelf:
            request = MockRequest()
            max_retries = 3
            
            def retry(self, exc=None, countdown=None):
                # For sync execution, we don't actually retry
                raise exc
        
        try:
            return send_testimonial_notification_email(
                MockSelf(), 
                testimonial_id, 
                email_type, 
                recipient_email, 
                context_data
            )
        except Exception as e:
            logger.error(f"Error sending testimonial email: {e}")
            return None


def send_admin_notification(testimonial_id: str, notification_type: str):
    """
    Wrapper function to send admin notifications.
    
    Args:
        testimonial_id: ID of the testimonial
        notification_type: Type of notification (new_testimonial, etc.)
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return send_admin_notification_email.delay(testimonial_id, notification_type)
    else:
        class MockRequest:
            retries = 0
        
        class MockSelf:
            request = MockRequest()
            max_retries = 3
            
            def retry(self, exc=None, countdown=None):
                raise exc
        
        try:
            return send_admin_notification_email(MockSelf(), testimonial_id, notification_type)
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
            return None


def process_media(media_id: str):
    """
    Wrapper function to process media files.
    
    Args:
        media_id: ID of the media file
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return process_testimonial_media.delay(media_id)
    else:
        class MockRequest:
            retries = 0
        
        class MockSelf:
            request = MockRequest()
            max_retries = 3
            
            def retry(self, exc=None, countdown=None):
                raise exc
        
        try:
            return process_testimonial_media(MockSelf(), media_id)
        except Exception as e:
            logger.error(f"Error processing media: {e}")
            return None


def bulk_moderate(testimonial_ids: list, action: str, user_id: int = None, 
                 extra_data: Dict[str, Any] = None):
    """
    Wrapper function for bulk moderation.
    
    Args:
        testimonial_ids: List of testimonial IDs
        action: Moderation action to perform
        user_id: ID of user performing action
        extra_data: Additional data for the action
    """
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return bulk_moderate_testimonials.delay(testimonial_ids, action, user_id, extra_data)
    else:
        class MockRequest:
            retries = 0
        
        class MockSelf:
            request = MockRequest()
            max_retries = 2  # bulk_moderate_testimonials has max_retries=2
            
            def retry(self, exc=None, countdown=None):
                raise exc
        
        try:
            return bulk_moderate_testimonials(MockSelf(), testimonial_ids, action, user_id, extra_data)
        except Exception as e:
            logger.error(f"Error in bulk moderation: {e}")
            return None