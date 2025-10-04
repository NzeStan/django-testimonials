# testimonials/tasks.py - UPDATED WITH THUMBNAIL GENERATION

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
    # When Celery is not available, create a decorator that removes the bind parameter
    def shared_task(*args, **kwargs):
        def decorator(func):
            kwargs.pop('bind', None)
            kwargs.pop('max_retries', None)
            kwargs.pop('default_retry_delay', None)
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


# === EMAIL TASKS === (keeping existing email implementation)

if CELERY_AVAILABLE:
    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def send_testimonial_notification_email(self, testimonial_id: str, email_type: str, 
                                           recipient_email: str, context_data: Dict[str, Any] = None):
        """Send testimonial-related notification emails (Celery version with self)."""
        return _send_testimonial_notification_email_impl(
            self, testimonial_id, email_type, recipient_email, context_data
        )
else:
    def send_testimonial_notification_email(testimonial_id: str, email_type: str, 
                                           recipient_email: str, context_data: Dict[str, Any] = None):
        """Send testimonial-related notification emails (non-Celery version without self)."""
        return _send_testimonial_notification_email_impl(
            None, testimonial_id, email_type, recipient_email, context_data
        )


def _send_testimonial_notification_email_impl(self, testimonial_id: str, email_type: str, 
                                              recipient_email: str, context_data: Dict[str, Any] = None):
    """Implementation of send_testimonial_notification_email."""
    if not app_settings.SEND_EMAIL_NOTIFICATIONS:
        logger.info(f"Email notifications disabled. Skipping {email_type} email for testimonial {testimonial_id}")
        return
    
    try:
        from .models import Testimonial
        
        testimonial = Testimonial.objects.select_related('category', 'author').get(id=testimonial_id)
        
        context = {
            'testimonial': testimonial,
            'site_name': getattr(settings, 'SITE_NAME', 'Django Testimonials'),
            'site_url': getattr(settings, 'SITE_URL', ''),
        }
        
        if context_data:
            context.update(context_data)
        
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
        }
        
        template_config = templates.get(email_type)
        if not template_config:
            logger.error(f"Unknown email type: {email_type}")
            return
        
        subject = render_to_string(template_config['subject'], context).strip()
        text_message = render_to_string(template_config['body_text'], context)
        
        from_name = app_settings.EMAIL_FROM_NAME
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        from_address = f"{from_name} <{from_email}>"
        
        if app_settings.USE_HTML_EMAILS:
            try:
                html_message = render_to_string(template_config['body_html'], context)
                
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
                send_mail(
                    subject=subject,
                    message=text_message,
                    from_email=from_address,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
        else:
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
        
        if self and hasattr(self, 'request') and hasattr(self, 'retry'):
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(f"Final failure sending {email_type} email for testimonial {testimonial_id}")


# === ADMIN NOTIFICATION TASKS === (keeping existing implementation)

if CELERY_AVAILABLE:
    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def send_admin_notification_email(self, testimonial_id: str, notification_type: str):
        """Send admin notification emails (Celery version)."""
        return _send_admin_notification_email_impl(self, testimonial_id, notification_type)
else:
    def send_admin_notification_email(testimonial_id: str, notification_type: str):
        """Send admin notification emails (non-Celery version)."""
        return _send_admin_notification_email_impl(None, testimonial_id, notification_type)


def _send_admin_notification_email_impl(self, testimonial_id: str, notification_type: str):
    """Implementation of send_admin_notification_email."""
    if not app_settings.SEND_ADMIN_NOTIFICATIONS:
        logger.info(f"Admin notifications disabled. Skipping {notification_type} notification for testimonial {testimonial_id}")
        return
    
    try:
        from .models import Testimonial
        
        admin_email = app_settings.NOTIFICATION_EMAIL
        if not admin_email:
            logger.warning(f"No admin notification email configured. Skipping {notification_type} notification.")
            return
        
        testimonial = Testimonial.objects.select_related('category', 'author').get(id=testimonial_id)
        
        context = {
            'testimonial': testimonial,
            'site_name': getattr(settings, 'SITE_NAME', 'Django Testimonials'),
            'site_url': getattr(settings, 'SITE_URL', ''),
            'notification_type': notification_type,
        }
        
        subject = render_to_string('testimonials/emails/new_testimonial_subject.txt', context).strip()
        text_message = render_to_string('testimonials/emails/new_testimonial_body.txt', context)
        
        from_name = app_settings.EMAIL_FROM_NAME
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        from_address = f"{from_name} <{from_email}>"
        
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
        
        if self and hasattr(self, 'request') and hasattr(self, 'retry'):
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# === MEDIA PROCESSING TASKS === (UPDATED WITH THUMBNAIL GENERATION)

if CELERY_AVAILABLE:
    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def process_testimonial_media(self, media_id: str):
        """Process testimonial media (Celery version)."""
        return _process_testimonial_media_impl(self, media_id)
else:
    def process_testimonial_media(media_id: str):
        """Process testimonial media (non-Celery version)."""
        return _process_testimonial_media_impl(None, media_id)


def _process_testimonial_media_impl(self, media_id: str):
    """
    Implementation of process_testimonial_media.
    
    ✅ NOW GENERATES THUMBNAILS FOR IMAGES!
    """
    try:
        from .models import TestimonialMedia
        from .constants import TestimonialMediaType
        
        media = TestimonialMedia.objects.select_related('testimonial').get(id=media_id)
        
        # ✅ THUMBNAIL GENERATION IMPLEMENTATION
        if media.media_type == TestimonialMediaType.IMAGE and app_settings.ENABLE_THUMBNAILS:
            logger.info(f"Generating thumbnails for media {media_id}")
            
            # Generate thumbnails and store in extra_data
            thumbnails = generate_thumbnails(media.file, app_settings.THUMBNAIL_SIZES)
            
            if thumbnails:
                # Initialize extra_data if None
                if media.extra_data is None:
                    media.extra_data = {}
                
                # Store thumbnail info
                media.extra_data['thumbnails'] = {}
                
                for size_name, thumbnail_file in thumbnails.items():
                    # Save thumbnail file
                    thumbnail_filename = f"thumb_{size_name}_{media.file.name.split('/')[-1]}"
                    media.file.storage.save(thumbnail_filename, thumbnail_file)
                    
                    # Store thumbnail path in extra_data
                    media.extra_data['thumbnails'][size_name] = thumbnail_filename
                    
                    logger.info(f"Generated {size_name} thumbnail for media {media_id}: {thumbnail_filename}")
                
                # Save media with thumbnail info
                media.save(update_fields=['extra_data'])
                
                logger.info(f"Successfully generated {len(thumbnails)} thumbnails for media {media_id}")
            else:
                logger.warning(f"No thumbnails generated for media {media_id}")
        
        elif media.media_type == TestimonialMediaType.VIDEO:
            logger.info(f"Video processing for media {media_id} - placeholder for future implementation")
            # Future: Add video thumbnail extraction here
            
        elif media.media_type == TestimonialMediaType.AUDIO:
            logger.info(f"Audio processing for media {media_id} - placeholder for future implementation")
            # Future: Add audio waveform generation here
        
        # Log successful processing
        log_testimonial_action(
            media.testimonial,
            "media_processed",
            extra_data={
                'media_id': str(media_id),
                'media_type': media.media_type,
                'thumbnails_generated': bool(media.extra_data and 'thumbnails' in media.extra_data)
            }
        )
        
        # Invalidate cache
        invalidate_testimonial_cache(testimonial_id=media.testimonial_id)
        
    except Exception as exc:
        logger.error(f"Failed to process media {media_id}: {exc}")
        
        if self and hasattr(self, 'request') and hasattr(self, 'retry'):
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# === BULK OPERATIONS TASKS === (keeping existing implementation)

if CELERY_AVAILABLE:
    @shared_task(bind=True, max_retries=2, default_retry_delay=120)
    def bulk_moderate_testimonials(self, testimonial_ids: list, action: str, user_id: int = None, 
                                  extra_data: Dict[str, Any] = None):
        """Bulk moderate testimonials (Celery version)."""
        return _bulk_moderate_testimonials_impl(self, testimonial_ids, action, user_id, extra_data)
else:
    def bulk_moderate_testimonials(testimonial_ids: list, action: str, user_id: int = None, 
                                  extra_data: Dict[str, Any] = None):
        """Bulk moderate testimonials (non-Celery version)."""
        return _bulk_moderate_testimonials_impl(None, testimonial_ids, action, user_id, extra_data)


def _bulk_moderate_testimonials_impl(self, testimonial_ids: list, action: str, user_id: int = None, 
                                    extra_data: Dict[str, Any] = None):
    """Implementation of bulk_moderate_testimonials."""
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
                    if user:
                        testimonial.approved_by = user
                        testimonial.approved_at = timezone.now()
                    testimonial.save()
                    updated_count += 1
            
            elif action == 'reject':
                if testimonial.status != TestimonialStatus.REJECTED:
                    testimonial.status = TestimonialStatus.REJECTED
                    if extra_data and 'rejection_reason' in extra_data:
                        testimonial.rejection_reason = extra_data['rejection_reason']
                    else:
                        testimonial.rejection_reason = "Bulk rejection"
                    testimonial.save()
                    updated_count += 1
            
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
            
            elif action == 'verify':
                if not testimonial.is_verified:
                    testimonial.is_verified = True
                    testimonial.save()
                    updated_count += 1
            
            elif action == 'unverify':
                if testimonial.is_verified:
                    testimonial.is_verified = False
                    testimonial.save()
                    updated_count += 1
        
        # Log bulk action
        if updated_count > 0:
            log_testimonial_action(
                None,
                f"bulk_{action}",
                user,
                f"Bulk {action}: {updated_count}/{len(testimonials)} testimonials updated",
                {
                    'testimonial_ids': testimonial_ids,
                    'action': action,
                    'updated_count': updated_count,
                    'total_count': len(testimonials)
                }
            )
        
        # Invalidate cache for all affected testimonials
        invalidate_testimonial_cache()
        
        logger.info(f"Bulk {action} completed: {updated_count}/{len(testimonials)} testimonials updated")
        
        return {
            'success': True,
            'updated_count': updated_count,
            'total': len(testimonials),
            'action': action
        }
        
    except Exception as exc:
        logger.error(f"Bulk moderation failed for action '{action}': {exc}")
        
        if self and hasattr(self, 'request') and hasattr(self, 'retry'):
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': str(exc),
            'action': action
        }

# === CACHE MANAGEMENT TASKS ===

@shared_task
def cleanup_expired_cache():
    """Clean up expired cache entries."""
    try:
        if app_settings.USE_REDIS_CACHE:
            logger.info("Cache cleanup completed")
    except Exception as exc:
        logger.error(f"Cache cleanup failed: {exc}")


@shared_task
def generate_testimonial_stats():
    """Generate and cache testimonial statistics."""
    try:
        from .models import Testimonial
        from .constants import TestimonialStatus
        
        stats = {
            'total': Testimonial.objects.count(),
            'approved': Testimonial.objects.filter(status=TestimonialStatus.APPROVED).count(),
            'pending': Testimonial.objects.filter(status=TestimonialStatus.PENDING).count(),
            'featured': Testimonial.objects.filter(status=TestimonialStatus.FEATURED).count(),
        }
        
        from django.core.cache import cache
        from .utils import get_cache_key
        cache.set(get_cache_key('stats'), stats, timeout=app_settings.CACHE_TIMEOUT)
        
        logger.info(f"Testimonial stats generated: {stats}")
        
    except Exception as exc:
        logger.error(f"Stats generation failed: {exc}")


@shared_task
def optimize_database():
    """Run database optimization tasks."""
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("ANALYZE testimonials_testimonial;")
                cursor.execute("ANALYZE testimonials_testimonialcategory;")
                cursor.execute("ANALYZE testimonials_testimonialmedia;")
        
        logger.info("Database optimization completed")
        
    except Exception as exc:
        logger.error(f"Database optimization failed: {exc}")


# === PERIODIC TASK SCHEDULE ===

if CELERY_AVAILABLE:
    from celery.schedules import crontab
    
    PERIODIC_TASKS = {
        'cleanup-expired-cache': {
            'task': 'testimonials.tasks.cleanup_expired_cache',
            'schedule': crontab(minute=0, hour='*/6'),
        },
        'generate-testimonial-stats': {
            'task': 'testimonials.tasks.generate_testimonial_stats',
            'schedule': crontab(minute=0, hour='*/1'),
        },
        'optimize-database': {
            'task': 'testimonials.tasks.optimize_database',
            'schedule': crontab(minute=0, hour=3),
        },
    }


# === TASK WRAPPER FUNCTIONS ===

def send_testimonial_email(testimonial_id: str, email_type: str, 
                          recipient_email: str, context_data: Dict[str, Any] = None):
    """Wrapper to send testimonial emails (async if Celery enabled, sync otherwise)."""
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return send_testimonial_notification_email.delay(
            testimonial_id, email_type, recipient_email, context_data
        )
    else:
        return send_testimonial_notification_email(
            testimonial_id, email_type, recipient_email, context_data
        )


def send_admin_notification(testimonial_id: str, notification_type: str):
    """Wrapper to send admin notifications."""
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return send_admin_notification_email.delay(testimonial_id, notification_type)
    else:
        return send_admin_notification_email(testimonial_id, notification_type)


def process_media(media_id: str):
    """Wrapper to process media files."""
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return process_testimonial_media.delay(media_id)
    else:
        return process_testimonial_media(media_id)


def bulk_moderate(testimonial_ids: list, action: str, user_id: int = None, 
                 extra_data: Dict[str, Any] = None):
    """Wrapper for bulk moderation."""
    if app_settings.USE_CELERY and CELERY_AVAILABLE:
        return bulk_moderate_testimonials.delay(testimonial_ids, action, user_id, extra_data)
    else:
        return bulk_moderate_testimonials(testimonial_ids, action, user_id, extra_data)