# testimonials/signals.py - REFACTORED

"""
Refactored signals using services for cache and task management.
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import Signal, receiver
from django.utils import timezone

from .models import Testimonial, TestimonialMedia
from .constants import TestimonialStatus
from .conf import app_settings

# Import services instead of utils
from .services import TestimonialCacheService, TaskExecutor
from .utils import log_testimonial_action

logger = logging.getLogger("testimonials")

# Custom signals
testimonial_approved = Signal()
testimonial_rejected = Signal()
testimonial_featured = Signal()
testimonial_archived = Signal()
testimonial_responded = Signal()
testimonial_created = Signal()
testimonial_media_added = Signal()


@receiver(pre_save, sender=Testimonial)
def testimonial_pre_save(sender, instance, **kwargs):
    """
    Pre-save handler for testimonials.
    Handles status changes and logging.
    """
    if not instance.pk:
        return
    
    update_fields = kwargs.get('update_fields', None)
    
    # Load old instance for comparison
    try:
        if update_fields:
            fields_to_load = ['status', 'response', 'approved_at', 'approved_by']
            old_instance = Testimonial.objects.only(*fields_to_load).get(pk=instance.pk)
        else:
            old_instance = Testimonial.objects.only(
                'status', 'response', 'approved_at', 'approved_by'
            ).get(pk=instance.pk)
    except Testimonial.DoesNotExist:
        return
    
    # Handle status changes
    if old_instance.status != instance.status:
        logger.info(
            f"Testimonial ID {instance.pk} status changed from "
            f"{old_instance.status} to {instance.status}"
        )
        
        # Handle APPROVED
        if instance.status == TestimonialStatus.APPROVED:
            if not instance.approved_at:
                instance.approved_at = timezone.now()
            
            testimonial_approved.send(sender=sender, instance=instance)
            
            # Send approval email using TaskExecutor
            if app_settings.SEND_EMAIL_NOTIFICATIONS and instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    TaskExecutor.execute(
                        send_testimonial_email,
                        str(instance.pk),
                        'approved',
                        instance.author_email
                    )
                    logger.info(f"Approval email queued for testimonial {instance.pk}")
                except Exception as e:
                    logger.error(f"Error queuing approval email: {e}")
        
        # Handle REJECTED
        elif instance.status == TestimonialStatus.REJECTED:
            if not instance.rejection_reason:
                instance.rejection_reason = "Status changed to rejected."
            
            testimonial_rejected.send(
                sender=sender,
                instance=instance,
                reason=instance.rejection_reason
            )
            
            # Send rejection email using TaskExecutor
            if app_settings.SEND_EMAIL_NOTIFICATIONS and instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    TaskExecutor.execute(
                        send_testimonial_email,
                        str(instance.pk),
                        'rejected',
                        instance.author_email
                    )
                    logger.info(f"Rejection email queued for testimonial {instance.pk}")
                except Exception as e:
                    logger.error(f"Error queuing rejection email: {e}")
        
        # Handle FEATURED
        elif instance.status == TestimonialStatus.FEATURED:
            testimonial_featured.send(sender=sender, instance=instance)
        
        # Handle ARCHIVED
        elif instance.status == TestimonialStatus.ARCHIVED:
            testimonial_archived.send(sender=sender, instance=instance)


@receiver(post_save, sender=Testimonial)
def testimonial_post_save(sender, instance, created, **kwargs):
    """
    Post-save handler for testimonials.
    Handles cache invalidation and notifications.
    """
    # Send creation signal
    if created:
        testimonial_created.send(sender=sender, instance=instance)
        log_testimonial_action(instance, "create", None)
        
        # Send admin notification using TaskExecutor
        if app_settings.SEND_EMAIL_NOTIFICATIONS:
            try:
                from .tasks import send_admin_notification
                TaskExecutor.execute(
                    send_admin_notification,
                    str(instance.pk),
                    'new_testimonial'
                )
            except Exception as e:
                logger.error(f"Error queuing admin notification: {e}")
    
    # Invalidate cache using CacheService
    TestimonialCacheService.invalidate_testimonial(
        testimonial_id=instance.pk,
        category_id=instance.category_id,
        user_id=instance.author_id
    )


@receiver(post_delete, sender=Testimonial)
def testimonial_post_delete(sender, instance, **kwargs):
    """
    Post-delete handler for testimonials.
    Handles cache invalidation and cleanup.
    """
    # Log deletion
    log_testimonial_action(instance, "delete", None)
    
    # Invalidate cache using CacheService
    TestimonialCacheService.invalidate_testimonial(
        testimonial_id=instance.pk,
        category_id=instance.category_id,
        user_id=instance.author_id
    )


@receiver(post_save, sender=TestimonialMedia)
def media_post_save(sender, instance, created, **kwargs):
    """
    Post-save handler for testimonial media.
    Handles media processing and cache invalidation.
    """
    if created:
        testimonial_media_added.send(sender=sender, instance=instance)
        
        # Process media asynchronously using TaskExecutor
        if app_settings.USE_CELERY:
            try:
                from .tasks import process_media
                TaskExecutor.execute(process_media, str(instance.pk))
            except Exception as e:
                logger.error(f"Error queuing media processing: {e}")
    
    # Invalidate cache using CacheService
    TestimonialCacheService.invalidate_media(
        media_id=instance.pk,
        testimonial_id=instance.testimonial_id
    )


@receiver(post_delete, sender=TestimonialMedia)
def media_post_delete(sender, instance, **kwargs):
    """
    Post-delete handler for testimonial media.
    Handles cache invalidation and file cleanup.
    """
    # Invalidate cache using CacheService
    TestimonialCacheService.invalidate_media(
        media_id=instance.pk,
        testimonial_id=instance.testimonial_id
    )
    
    # Delete physical file
    if instance.file:
        try:
            import os
            if os.path.isfile(instance.file.path):
                os.remove(instance.file.path)
                logger.info(f"Deleted media file: {instance.file.path}")
        except Exception as e:
            logger.error(f"Error deleting media file: {e}")