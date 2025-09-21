import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import Signal, receiver
from django.utils import timezone
from django.conf import settings
from .models import Testimonial, TestimonialMedia
from .constants import TestimonialStatus
from .conf import app_settings
from .utils import invalidate_testimonial_cache, execute_task

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
    """
    if not instance.pk:  # Skip for new objects
        return

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
            
            # Send approval email (async if Celery enabled)
            if instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    execute_task(
                        send_testimonial_email,
                        str(instance.pk),
                        'approved',
                        instance.author_email
                    )
                except Exception as e:
                    logger.error(f"Error queuing approval email: {e}")

        # Handle REJECTED
        elif instance.status == TestimonialStatus.REJECTED:
            if not instance.rejection_reason:
                instance.rejection_reason = "Status changed from approved to rejected."

            testimonial_rejected.send(
                sender=sender, instance=instance, reason=instance.rejection_reason
            )

            # Send rejection email (async if Celery enabled)
            if instance.author_email:
                try:
                    from .tasks import send_testimonial_email
                    execute_task(
                        send_testimonial_email,
                        str(instance.pk),
                        'rejected',
                        instance.author_email,
                        {'reason': instance.rejection_reason}
                    )
                except Exception as e:
                    logger.error(f"Error queuing rejection email: {e}")

        # Handle FEATURED
        elif instance.status == TestimonialStatus.FEATURED:
            testimonial_featured.send(sender=sender, instance=instance)

        # Handle ARCHIVED
        elif instance.status == TestimonialStatus.ARCHIVED:
            testimonial_archived.send(sender=sender, instance=instance)

        # Invalidate cache for status changes
        invalidate_testimonial_cache(
            testimonial_id=instance.pk,
            category_id=instance.category_id,
            user_id=instance.author_id
        )

    # --- Response added ---
    if not old_instance.response and instance.response:
        testimonial_responded.send(
            sender=sender, instance=instance, response=instance.response
        )

        # Send response email (async if Celery enabled)
        if instance.author_email:
            try:
                from .tasks import send_testimonial_email
                execute_task(
                    send_testimonial_email,
                    str(instance.pk),
                    'response',
                    instance.author_email,
                    {'response': instance.response}
                )
            except Exception as e:
                logger.error(f"Error queuing response email: {e}")


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

    # Send admin notification (async if Celery enabled)
    if app_settings.NOTIFICATION_EMAIL:
        try:
            from .tasks import send_admin_notification
            execute_task(
                send_admin_notification,
                str(instance.pk),
                'new_testimonial'
            )
        except Exception as e:
            logger.error(f"Error queuing admin notification: {e}")

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
            from .tasks import process_media
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
    invalidate_testimonial_cache(
        testimonial_id=instance.pk,
        category_id=instance.category_id,
        user_id=instance.author_id
    )
    
    # Specifically invalidate featured testimonials if this becomes featured
    if instance.status == TestimonialStatus.FEATURED:
        from .utils import get_cache_key
        from django.core.cache import cache
        try:
            cache.delete(get_cache_key('featured_testimonials'))
        except Exception as e:
            logger.warning(f"Failed to invalidate featured testimonials cache: {e}")


@receiver(testimonial_featured)
def invalidate_cache_on_feature(sender, instance, **kwargs):
    """Invalidate cache when a testimonial is featured."""
    from .utils import get_cache_key
    from django.core.cache import cache
    
    try:
        # Invalidate featured testimonials cache
        cache.delete(get_cache_key('featured_testimonials'))
        
        # Invalidate general caches
        invalidate_testimonial_cache(
            testimonial_id=instance.pk,
            category_id=instance.category_id,
            user_id=instance.author_id
        )
    except Exception as e:
        logger.warning(f"Failed to invalidate cache on feature: {e}")


# === PERFORMANCE MONITORING SIGNAL HANDLERS ===

@receiver(testimonial_created)
def monitor_testimonial_creation_rate(sender, instance, **kwargs):
    """Monitor testimonial creation rate for performance insights."""
    try:
        from django.core.cache import cache
        from .utils import get_cache_key
        
        # Increment daily counter
        today = timezone.now().date().isoformat()
        counter_key = get_cache_key('daily_testimonial_count', today)
        
        if app_settings.USE_REDIS_CACHE:
            current_count = cache.get(counter_key, 0)
            cache.set(counter_key, current_count + 1, timeout=86400)  # 24 hours
            
            # Log if high volume
            if current_count > 100:  # Threshold for high volume
                logger.info(f"High testimonial volume detected: {current_count} testimonials today")
                
    except Exception as e:
        logger.warning(f"Failed to monitor testimonial creation rate: {e}")


# === EXAMPLE CUSTOM SIGNAL HANDLERS ===
# These are examples that can be connected in the integrating application

def notify_admin_on_testimonial_created(sender, instance, **kwargs):
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
    from .utils import log_testimonial_action
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
    from .utils import log_testimonial_action
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
    try:
        # This is a placeholder for search index integration
        # In a real implementation, this would update Elasticsearch, Solr, etc.
        logger.debug(f"Updating search index for published testimonial {instance.pk}")
        
        # Example: Add to search index
        # search_index.add_document({
        #     'id': str(instance.pk),
        #     'content': instance.content,
        #     'author': instance.author_name,
        #     'rating': instance.rating,
        #     'category': instance.category.name if instance.category else None,
        #     'status': instance.status,
        #     'created_at': instance.created_at.isoformat(),
        # })
        
    except Exception as e:
        logger.warning(f"Failed to update search index: {e}")


@receiver(testimonial_archived)
@receiver(testimonial_rejected)
def remove_from_search_index_on_unpublish(sender, instance, **kwargs):
    """Remove from search index when testimonial is unpublished."""
    try:
        # This is a placeholder for search index integration
        logger.debug(f"Removing testimonial {instance.pk} from search index")
        
        # Example: Remove from search index
        # search_index.remove_document(str(instance.pk))
        
    except Exception as e:
        logger.warning(f"Failed to remove from search index: {e}")


# These signal connections are examples and can be uncommented based on needs:
# testimonial_created.connect(notify_admin_on_testimonial_created)
# testimonial_approved.connect(update_statistics_on_testimonial_approved)
# testimonial_rejected.connect(log_testimonial_rejection)
# testimonial_approved.connect(update_user_reputation_on_approval)
# testimonial_featured.connect(trigger_recommendation_update)