# testimonials/signals.py

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import Signal, receiver
from django.utils import timezone
from django.conf import settings
from .models import Testimonial, TestimonialMedia
from .constants import TestimonialStatus
from .conf import app_settings
from .utils import invalidate_testimonial_cache, execute_task
from .utils import get_cache_key
from django.core.cache import cache
from .tasks import process_media
from .utils import log_testimonial_action

# Set up logging
logger = logging.getLogger("testimonials")

# Custom signals
testimonial_approved = Signal()  # Provides sender, instance
testimonial_rejected = Signal()  # Provides sender, instance, reason
testimonial_featured = Signal()  # Provides sender, instance
testimonial_archived = Signal()  # Provides sender, instance
testimonial_responded = Signal()  # Provides sender, instance, response
testimonial_created = Signal()   # Provides sender, instance
testimonial_media_added = Signal()  # Provides sender, instance


@receiver(pre_save, sender=Testimonial)
def testimonial_pre_save(sender, instance, **kwargs):
    """
    Optimized pre-save handler for testimonials.
    Handles status changes, logging, and cache invalidation.
    FIXED: Now works correctly with update_fields parameter.
    """
    if not instance.pk:  # Skip for new objects
        return

    # CRITICAL FIX: Check if response is being updated
    update_fields = kwargs.get('update_fields', None)
    
    # If update_fields is specified and 'response' is in it, load only necessary fields
    if update_fields:
        fields_to_load = ['status', 'response', 'approved_at', 'approved_by']
        # Only load fields that we need for comparison
        try:
            old_instance = Testimonial.objects.only(*fields_to_load).get(pk=instance.pk)
        except Testimonial.DoesNotExist:
            return
    else:
        # Load all fields normally
        try:
            old_instance = Testimonial.objects.only(
                'status', 'response', 'approved_at', 'approved_by'
            ).get(pk=instance.pk)
        except Testimonial.DoesNotExist:
            return

    # --- Status changed ---
    if old_instance.status != instance.status:
        logger.info(
            f"Testimonial ID {instance.pk} status changed from "
            f"{old_instance.status} to {instance.status}"
        )

        # Handle APPROVED
        if instance.status == TestimonialStatus.APPROVED:
            logger.info(f"Sending testimonial_approved signal for {instance.pk}")
            if not instance.approved_at:
                instance.approved_at = timezone.now()
            
            # Send signal
            testimonial_approved.send(sender=sender, instance=instance)
            
            # Send approval email (async if Celery enabled) - CHECK SETTINGS FIRST
            if app_settings.SEND_EMAIL_NOTIFICATIONS and instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    execute_task(
                        send_testimonial_email,
                        str(instance.pk),
                        'approved',
                        instance.author_email
                    )
                    logger.info(f"Approval email queued for testimonial {instance.pk}")
                except Exception as e:
                    logger.error(f"Error queuing approval email: {e}")
            else:
                if not app_settings.SEND_EMAIL_NOTIFICATIONS:
                    logger.debug(f"Email notifications disabled - skipping approval email for {instance.pk}")
                elif not instance.author_email:
                    logger.debug(f"No author email - skipping approval email for {instance.pk}")

        # Handle REJECTED
        elif instance.status == TestimonialStatus.REJECTED:
            if not instance.rejection_reason:
                instance.rejection_reason = "Status changed to rejected."
            
            logger.info(f"Sending testimonial_rejected signal for {instance.pk}")
            testimonial_rejected.send(
                sender=sender, instance=instance, reason=instance.rejection_reason
            )

            # Send rejection email (async if Celery enabled) - CHECK SETTINGS FIRST
            if app_settings.SEND_EMAIL_NOTIFICATIONS and instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    execute_task(
                        send_testimonial_email,
                        str(instance.pk),
                        'rejected',
                        instance.author_email,
                        {'reason': instance.rejection_reason}
                    )
                    logger.info(f"Rejection email queued for testimonial {instance.pk}")
                except Exception as e:
                    logger.error(f"Error queuing rejection email: {e}")
            else:
                if not app_settings.SEND_EMAIL_NOTIFICATIONS:
                    logger.debug(f"Email notifications disabled - skipping rejection email for {instance.pk}")
                elif not instance.author_email:
                    logger.debug(f"No author email - skipping rejection email for {instance.pk}")

        # Handle FEATURED
        elif instance.status == TestimonialStatus.FEATURED:
            logger.info(f"Testimonial {instance.pk} featured")
            testimonial_featured.send(sender=sender, instance=instance)

        # Handle ARCHIVED
        elif instance.status == TestimonialStatus.ARCHIVED:
            logger.info(f"Testimonial {instance.pk} archived")
            testimonial_archived.send(sender=sender, instance=instance)

        # Invalidate cache for status changes
        invalidate_testimonial_cache(
            testimonial_id=instance.pk,
            category_id=instance.category_id,
            user_id=instance.author_id
        )

    # --- Response added ---
    # ✅ FIXED: Check if 'response' is being updated (either in update_fields or changed)
    if update_fields is None or 'response' in update_fields:
        # Only check for response changes if response field is being updated
        if not old_instance.response and instance.response:
            logger.info(f"Response added to testimonial {instance.pk}")
            testimonial_responded.send(
                sender=sender, instance=instance, response=instance.response
            )

            # Send response email (async if Celery enabled) - CHECK SETTINGS FIRST
            if app_settings.SEND_EMAIL_NOTIFICATIONS and instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    execute_task(
                        send_testimonial_email,
                        str(instance.pk),
                        'response',
                        instance.author_email,
                        {'response': instance.response}
                    )
                    logger.info(f"Response email queued for testimonial {instance.pk}")
                except Exception as e:
                    logger.error(f"Error queuing response email: {e}")
            else:
                if not app_settings.SEND_EMAIL_NOTIFICATIONS:
                    logger.debug(f"Email notifications disabled - skipping response email for {instance.pk}")
                elif not instance.author_email:
                    logger.debug(f"No author email - skipping response email for {instance.pk}")


@receiver(post_save, sender=Testimonial)
def testimonial_post_save(sender, instance, created, **kwargs):
    """
    Optimized post-save handler for testimonials.
    Handles new testimonial creation and cache invalidation.
    """
    if not created:
        # For updates, just invalidate cache
        invalidate_testimonial_cache(
            testimonial_id=instance.pk,
            category_id=instance.category_id,
            user_id=instance.author_id
        )
        return

    # Handle new testimonial creation
    testimonial_created.send(sender=sender, instance=instance)
    logger.info(f"New testimonial created: ID {instance.pk}")

    # Send admin notification (async if Celery enabled) - CHECK SETTINGS FIRST
    if app_settings.SEND_ADMIN_NOTIFICATIONS and app_settings.NOTIFICATION_EMAIL:
        try:
            from .tasks import send_admin_notification
            execute_task(
                send_admin_notification,
                str(instance.pk),
                'new_testimonial'
            )
            logger.info(f"Admin notification queued for new testimonial {instance.pk}")
        except Exception as e:
            logger.error(f"Error queuing admin notification: {e}")
    else:
        if not app_settings.SEND_ADMIN_NOTIFICATIONS:
            logger.debug(f"Admin notifications disabled - skipping notification for {instance.pk}")
        elif not app_settings.NOTIFICATION_EMAIL:
            logger.debug(f"No admin notification email configured - skipping notification for {instance.pk}")

    # Invalidate cache for new testimonial
    invalidate_testimonial_cache(
        testimonial_id=instance.pk,
        category_id=instance.category_id,
        user_id=instance.author_id
    )


@receiver(post_delete, sender=Testimonial)
def testimonial_post_delete(sender, instance, **kwargs):
    """
    Handle testimonial deletion and cache invalidation.
    """
    logger.info(f"Testimonial deleted: ID {instance.pk}")
    
    # Invalidate cache
    invalidate_testimonial_cache(
        testimonial_id=instance.pk,
        category_id=instance.category_id,
        user_id=instance.author_id
    )


@receiver(post_save, sender=TestimonialMedia)
def testimonial_media_post_save(sender, instance, created, **kwargs):
    """
    Optimized signal handler for TestimonialMedia post_save.
    Handles media processing and cache invalidation.
    """
    if created:
        testimonial_media_added.send(sender=sender, instance=instance)
        logger.info(f"New media added to testimonial ID {instance.testimonial_id}: {instance.media_type}")
        
        # Process media asynchronously (if Celery enabled)
        try:
            execute_task(process_media, str(instance.pk))
        except Exception as e:
            logger.error(f"Error queuing media processing: {e}")
    
    # Invalidate cache
    invalidate_testimonial_cache(testimonial_id=instance.testimonial_id)


@receiver(post_delete, sender=TestimonialMedia)
def testimonial_media_post_delete(sender, instance, **kwargs):
    """
    Handle media deletion and cache invalidation.
    """
    logger.info(f"Media deleted: ID {instance.pk} from testimonial {instance.testimonial_id}")
    
    # Invalidate cache
    invalidate_testimonial_cache(testimonial_id=instance.testimonial_id)


# === CACHE INVALIDATION SIGNAL HANDLERS ===

@receiver(testimonial_approved)
def invalidate_cache_on_approval(sender, instance, **kwargs):
    """Invalidate relevant cache entries when a testimonial is approved."""
    logger.debug(f"Invalidating cache on approval for testimonial {instance.pk}")
    invalidate_testimonial_cache(
        testimonial_id=instance.pk,
        category_id=instance.category_id
    )


@receiver(testimonial_rejected)
def invalidate_cache_on_rejection(sender, instance, **kwargs):
    """Invalidate relevant cache entries when a testimonial is rejected."""
    logger.debug(f"Invalidating cache on rejection for testimonial {instance.pk}")
    invalidate_testimonial_cache(
        testimonial_id=instance.pk,
        category_id=instance.category_id
    )


@receiver(testimonial_featured)
def invalidate_cache_on_feature(sender, instance, **kwargs):
    """Invalidate relevant cache entries when a testimonial is featured."""
    logger.debug(f"Invalidating cache on feature for testimonial {instance.pk}")
    invalidate_testimonial_cache(
        testimonial_id=instance.pk,
        category_id=instance.category_id
    )


# === EXAMPLE CUSTOM SIGNAL HANDLERS ===
# These are examples that developers can use or modify

def notify_admin_on_new_testimonial(sender, instance, **kwargs):
    """Example handler for testimonial_created signal."""
    logger.info(f"Admin notification for new testimonial: {instance.pk}")
    # Actual notification logic would go here


def update_statistics_on_testimonial_approved(sender, instance, **kwargs):
    """Example handler for testimonial_approved signal."""
    logger.info(f"Updating statistics after testimonial approval: {instance.pk}")
    # Actual statistics update logic would go here


def log_testimonial_rejection(sender, instance, reason, **kwargs):
    """Example handler for testimonial_rejected signal."""
    logger.info(f"Testimonial rejected: {instance.pk}, Reason: {reason}")
    # Additional logging or notification logic


def update_user_reputation_on_approval(sender, instance, **kwargs):
    """Example handler to update user reputation when testimonial is approved."""
    if instance.author:
        logger.info(f"Updating reputation for user {instance.author.id}")
        # Update user reputation logic would go here


def trigger_recommendation_update(sender, instance, **kwargs):
    """Example handler to trigger recommendation engine updates."""
    logger.info(f"Triggering recommendation update for testimonial {instance.pk}")
    # Machine learning recommendation update logic would go here


# === BULK OPERATION SIGNAL HANDLERS ===

def handle_bulk_approval(testimonial_ids, user=None):
    """
    Handle bulk approval operations with optimized cache invalidation.
    
    Args:
        testimonial_ids: List of testimonial IDs
        user: User performing the bulk action
    """
    logger.info(f"Handling bulk approval for {len(testimonial_ids)} testimonials")
    
    # Invalidate all relevant caches
    invalidate_testimonial_cache()
    
    # Log bulk action
    log_testimonial_action(
        None,  # No specific testimonial
        "bulk_approve",
        user,
        f"Approved {len(testimonial_ids)} testimonials",
        {'testimonial_ids': testimonial_ids}
    )


def handle_bulk_rejection(testimonial_ids, reason, user=None):
    """
    Handle bulk rejection operations with optimized cache invalidation.
    
    Args:
        testimonial_ids: List of testimonial IDs
        reason: Rejection reason
        user: User performing the bulk action
    """
    logger.info(f"Handling bulk rejection for {len(testimonial_ids)} testimonials")
    
    # Invalidate all relevant caches
    invalidate_testimonial_cache()
    
    # Log bulk action
    log_testimonial_action(
        None,  # No specific testimonial
        "bulk_reject",
        user,
        f"Rejected {len(testimonial_ids)} testimonials: {reason}",
        {'testimonial_ids': testimonial_ids, 'reason': reason}
    )


# === SEARCH INDEX SIGNAL HANDLERS ===

@receiver(testimonial_approved)
@receiver(testimonial_featured)
def update_search_index_on_publish(sender, instance, **kwargs):
    """Update search index when testimonial is published."""
    logger.debug(f"Updating search index for published testimonial {instance.pk}")
    # Search index update logic would go here


@receiver(testimonial_archived)
@receiver(testimonial_rejected)
def remove_from_search_index_on_unpublish(sender, instance, **kwargs):
    """Remove from search index when testimonial is unpublished."""
    logger.debug(f"Removing testimonial {instance.pk} from search index")
    # Search index removal logic would go here