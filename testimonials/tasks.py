# testimonials/tasks.py - WITH SEMANTIC TIMEOUTS

"""
Celery tasks with semantic timeout usage.
"""

import logging
from typing import Dict, Any
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from .conf import app_settings
from .utils import generate_thumbnails, log_testimonial_action
from .services import TestimonialCacheService

logger = logging.getLogger("testimonials")

# Try to import Celery components
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Fallback decorator when Celery not available
    def shared_task(*args, **kwargs):
        def decorator(func):
            kwargs.pop('bind', None)
            kwargs.pop('max_retries', None)
            kwargs.pop('default_retry_delay', None)
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


# === EMAIL TASKS ===

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_testimonial_notification_email(self, testimonial_id: str, email_type: str, 
                                       recipient_email: str, context_data: Dict[str, Any] = None):
    """Send testimonial-related notification emails."""
    if not app_settings.SEND_EMAIL_NOTIFICATIONS:
        logger.info(f"Email notifications disabled. Skipping email for testimonial {testimonial_id}")
        return
    
    try:
        from .models import Testimonial
        testimonial = Testimonial.objects.get(pk=testimonial_id)
    except Testimonial.DoesNotExist:
        logger.error(f"Testimonial {testimonial_id} not found for email notification")
        return
    
    # Prepare context
    context = context_data or {}
    context.update({
        'testimonial': testimonial,
        'site_name': getattr(settings, 'SITE_NAME', 'Our Site'),
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    })
    
    # Email templates mapping
    email_templates = {
        'approved': {
            'subject': 'Your testimonial has been approved',
            'template': 'testimonials/emails/testimonial_approved_body.html',
        },
        'rejected': {
            'subject': 'Update on your testimonial',
            'template': 'testimonials/emails/testimonial_rejected_body.html',
        },
        'featured': {
            'subject': 'Your testimonial has been featured!',
            'template': 'testimonials/emails/testimonial_approved_body.html',
        },
    }
    
    email_config = email_templates.get(email_type)
    if not email_config:
        logger.error(f"Unknown email type: {email_type}")
        return
    
    try:
        # Render email
        html_content = render_to_string(email_config['template'], context)
        
        # Send email
        msg = EmailMultiAlternatives(
            subject=email_config['subject'],
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        logger.info(f"Sent {email_type} email to {recipient_email} for testimonial {testimonial_id}")
        
    except Exception as e:
        logger.error(f"Error sending {email_type} email: {e}")
        if CELERY_AVAILABLE and hasattr(self, 'retry'):
            raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_admin_notification(self, testimonial_id: str, notification_type: str):
    """Send admin notification about new testimonials."""
    if not app_settings.SEND_EMAIL_NOTIFICATIONS:
        return
    
    try:
        from .models import Testimonial
        testimonial = Testimonial.objects.get(pk=testimonial_id)
    except Testimonial.DoesNotExist:
        logger.error(f"Testimonial {testimonial_id} not found for admin notification")
        return
    
    admin_emails = getattr(settings, 'ADMINS', [])
    if not admin_emails:
        logger.warning("No admin emails configured")
        return
    
    recipient_emails = [
        item[1] if isinstance(item, (tuple, list)) else item 
        for item in admin_emails
    ]
    
    context = {
        'testimonial': testimonial,
        'site_name': getattr(settings, 'SITE_NAME', 'Our Site'),
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'admin_url': f"{getattr(settings, 'SITE_URL', '')}/admin/testimonials/testimonial/{testimonial.pk}/change/",
    }
    
    try:
        html_content = render_to_string('testimonials/emails/new_testimonial_body.html', context)
        
        msg = EmailMultiAlternatives(
            subject=f'New Testimonial Submitted: {testimonial.author_name}',
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_emails
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        logger.info(f"Sent admin notification for testimonial {testimonial_id}")
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
        if CELERY_AVAILABLE and hasattr(self, 'retry'):
            raise self.retry(exc=e)


# === MEDIA PROCESSING TASKS ===

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def process_media(self, media_id: str):
    """
    Process uploaded media (generate thumbnails, etc.).
    """
    try:
        from .models import TestimonialMedia
        from .constants import TestimonialMediaType
        
        media = TestimonialMedia.objects.get(pk=media_id)
        
        # Process images
        if media.media_type == TestimonialMediaType.IMAGE and media.file:
            try:
                thumbnails = generate_thumbnails(media.file.path)
                
                if thumbnails:
                    # Store thumbnail info in extra_data
                    if not media.extra_data:
                        media.extra_data = {}
                    media.extra_data['thumbnails'] = thumbnails
                    media.save(update_fields=['extra_data'])
                    
                    logger.info(f"Generated {len(thumbnails)} thumbnails for media {media_id}")
                
            except Exception as e:
                logger.error(f"Error generating thumbnails for media {media_id}: {e}")
        
        # Invalidate cache
        TestimonialCacheService.invalidate_media(
            media_id=media.pk,
            testimonial_id=media.testimonial_id
        )
        
    except Exception as e:
        logger.error(f"Error processing media {media_id}: {e}")
        if CELERY_AVAILABLE and hasattr(self, 'retry'):
            raise self.retry(exc=e)


# === MAINTENANCE TASKS ===

@shared_task
def cleanup_old_rejected_testimonials(days_old=90):
    """
    Clean up old rejected testimonials.
    """
    from datetime import timedelta
    from .models import Testimonial
    from .constants import TestimonialStatus
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    old_rejected = Testimonial.objects.filter(
        status=TestimonialStatus.REJECTED,
        updated_at__lt=cutoff_date
    )
    
    count = old_rejected.count()
    
    if count > 0:
        old_rejected.delete()
        logger.info(f"Deleted {count} old rejected testimonials")
        
        # Invalidate all caches
        TestimonialCacheService.invalidate_all()
    
    return count


@shared_task
def generate_testimonial_report():
    """
    Generate periodic testimonial statistics report.
    Caches with stats timeout.
    """
    from .models import Testimonial
    
    stats = Testimonial.objects.get_stats()
    
    # Cache the report using semantic timeout
    TestimonialCacheService.cache_stats(stats)
    
    logger.info("Generated and cached testimonial statistics report")
    return stats


# === CACHE WARMING TASKS ===

@shared_task
def warm_testimonial_caches():
    """
    Pre-warm frequently accessed caches with appropriate timeouts.
    """
    from .models import Testimonial, TestimonialCategory
    
    logger.info("Starting cache warming...")
    
    # Warm testimonial stats (30 min timeout)
    stats = Testimonial.objects.get_stats()
    TestimonialCacheService.cache_stats(stats)
    
    # Warm featured testimonials (2 hour timeout)
    featured = list(Testimonial.objects.featured()[:10])
    TestimonialCacheService.cache_featured(featured)
    
    # Warm category stats (1 hour timeout)
    category_stats = TestimonialCategory.objects.get_stats()
    TestimonialCacheService.set(
        'testimonials:category_stats',
        category_stats,
        timeout_type='stable'  # ✅ 1 hour timeout
    )
    
    # Warm dashboard overview (5 min timeout - volatile)
    from .dashboard.views import dashboard_overview
    # Note: This would need request context, so we'll cache the data components instead
    
    logger.info("Cache warming completed")
    return True


# === PERIODIC CACHE REFRESH TASKS ===

@shared_task
def refresh_volatile_caches():
    """
    Refresh volatile caches (dashboard data, pending counts, etc.).
    Run frequently (every 5 minutes).
    """
    from .models import Testimonial
    from .constants import TestimonialStatus
    
    logger.info("Refreshing volatile caches...")
    
    # Refresh pending count (volatile data)
    pending_count = Testimonial.objects.filter(status=TestimonialStatus.PENDING).count()
    TestimonialCacheService.set(
        'testimonials:counts:pending',
        pending_count,
        timeout_type='volatile'  # ✅ 5 minute timeout
    )
    
    # Refresh today's count (volatile data)
    today_count = Testimonial.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    TestimonialCacheService.set(
        'testimonials:counts:today',
        today_count,
        timeout_type='volatile'
    )
    
    logger.info("Volatile caches refreshed")
    return True


@shared_task
def refresh_stats_caches():
    """
    Refresh statistics caches.
    Run every 30 minutes.
    """
    from .models import Testimonial, TestimonialCategory, TestimonialMedia
    
    logger.info("Refreshing statistics caches...")
    
    # Refresh testimonial stats
    testimonial_stats = Testimonial.objects.get_stats()
    TestimonialCacheService.cache_stats(testimonial_stats)
    
    # Refresh category stats
    category_stats = TestimonialCategory.objects.get_stats()
    TestimonialCacheService.set(
        'testimonials:category_stats',
        category_stats,
        timeout_type='stats'  # ✅ 30 minute timeout
    )
    
    # Refresh media stats
    media_stats = TestimonialMedia.objects.get_media_stats()
    TestimonialCacheService.set(
        'testimonials:media_stats',
        media_stats,
        timeout_type='stats'
    )
    
    logger.info("Statistics caches refreshed")
    return True


@shared_task
def refresh_stable_caches():
    """
    Refresh stable caches (featured testimonials, categories, etc.).
    Run every hour.
    """
    from .models import Testimonial, TestimonialCategory
    
    logger.info("Refreshing stable caches...")
    
    # Refresh featured testimonials
    featured = list(Testimonial.objects.featured()[:10])
    TestimonialCacheService.cache_featured(featured)
    
    # Refresh published testimonials list
    published = list(Testimonial.objects.published().order_by('-created_at')[:50])
    TestimonialCacheService.set(
        TestimonialCacheService.get_key('PUBLISHED'),
        published,
        timeout_type='stable'  # ✅ 1 hour timeout
    )
    
    # Refresh active categories
    categories = list(TestimonialCategory.objects.active())
    TestimonialCacheService.set(
        'testimonials:categories:active',
        categories,
        timeout_type='stable'
    )
    
    logger.info("Stable caches refreshed")
    return True


# Backwards compatible aliases
send_testimonial_email = send_testimonial_notification_email