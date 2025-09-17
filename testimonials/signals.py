import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import Signal, receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Testimonial, TestimonialMedia
from .constants import TestimonialStatus
from .conf import app_settings

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
    Handles:
    - Logging status changes
    - Managing approval/rejection fields
    - Sending notifications & signals for status changes and responses
    """
    if not instance.pk:  # skip for new objects
        return

    try:
        old_instance = Testimonial.objects.get(pk=instance.pk)
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
            testimonial_approved.send(sender=sender, instance=instance)

            if instance.author_email:
                try:
                    context = {
                        "testimonial": instance,
                        "site_name": getattr(settings, "SITE_NAME", "Django Testimonials"),
                        "site_url": getattr(settings, "SITE_URL", ""),
                    }
                    subject = render_to_string(
                        "testimonials/emails/testimonial_approved_subject.txt", context
                    ).strip()
                    message = render_to_string(
                        "testimonials/emails/testimonial_approved_body.txt", context
                    )
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[instance.author_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Error sending testimonial approval notification: {e}")

        # Handle REJECTED
        elif instance.status == TestimonialStatus.REJECTED:
            if not instance.rejection_reason:
                instance.rejection_reason = "Status changed from approved to rejected."

            testimonial_rejected.send(
                sender=sender, instance=instance, reason=instance.rejection_reason
            )

            if instance.author_email:
                try:
                    context = {
                        "testimonial": instance,
                        "reason": instance.rejection_reason,
                        "site_name": getattr(settings, "SITE_NAME", "Django Testimonials"),
                        "site_url": getattr(settings, "SITE_URL", ""),
                    }
                    subject = render_to_string(
                        "testimonials/emails/testimonial_rejected_subject.txt", context
                    ).strip()
                    message = render_to_string(
                        "testimonials/emails/testimonial_rejected_body.txt", context
                    )
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[instance.author_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Error sending testimonial rejection notification: {e}")

        # Handle FEATURED
        elif instance.status == TestimonialStatus.FEATURED:
            testimonial_featured.send(sender=sender, instance=instance)

        # Handle ARCHIVED
        elif instance.status == TestimonialStatus.ARCHIVED:
            testimonial_archived.send(sender=sender, instance=instance)

    # --- Response added ---
    if not old_instance.response and instance.response:
        testimonial_responded.send(
            sender=sender, instance=instance, response=instance.response
        )

        if instance.author_email:
            try:
                context = {
                    "testimonial": instance,
                    "response": instance.response,
                    "site_name": getattr(settings, "SITE_NAME", "Django Testimonials"),
                    "site_url": getattr(settings, "SITE_URL", ""),
                }
                subject = render_to_string(
                    "testimonials/emails/testimonial_response_subject.txt", context
                ).strip()
                message = render_to_string(
                    "testimonials/emails/testimonial_response_body.txt", context
                )
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.author_email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Error sending testimonial response notification: {e}")

@receiver(post_save, sender=Testimonial)
def testimonial_post_save(sender, instance, created, **kwargs):
    """
    Handles new testimonial creation.
    """
    if not created:
        return

    testimonial_created.send(sender=sender, instance=instance)
    logger.info(f"New testimonial created: ID {instance.pk}")

    if app_settings.NOTIFICATION_EMAIL:
        try:
            context = {
                "testimonial": instance,
                "site_name": getattr(settings, "SITE_NAME", "Django Testimonials"),
                "site_url": getattr(settings, "SITE_URL", ""),
            }
            subject = render_to_string(
                "testimonials/emails/new_testimonial_subject.txt", context
            ).strip()
            message = render_to_string(
                "testimonials/emails/new_testimonial_body.txt", context
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[app_settings.NOTIFICATION_EMAIL],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Error sending new testimonial notification: {e}")



@receiver(post_save, sender=TestimonialMedia)
def testimonial_media_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for TestimonialMedia post_save.
    Sends signals for media added.
    """
    if created:
        testimonial_media_added.send(sender=sender, instance=instance)
        logger.info(f"New media added to testimonial ID {instance.testimonial_id}: {instance.media_type}")


# Example custom signal handlers - these can be connected in the integrating app

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


# These would typically be connected in the integrating application,
# but can be uncommented here for default behavior
# testimonial_created.connect(notify_admin_on_testimonial_created)
# testimonial_approved.connect(update_statistics_on_testimonial_approved)
# testimonial_rejected.connect(log_testimonial_rejection)