# Signals Documentation

Django Testimonials provides a comprehensive signal system that allows you to connect custom functionality to various events in the testimonial lifecycle. This document describes all available signals and provides examples of their use.

## Available Signals

All signals are defined in `testimonials.signals` and provide the following information:

- `sender`: The model class that sent the signal
- `instance`: The actual instance that triggered the signal
- Additional specific arguments depending on the signal

### Testimonial Lifecycle Signals

#### `testimonial_created`

Sent when a new testimonial is created.

**Arguments**:
- `sender`: The testimonial model class
- `instance`: The newly created testimonial instance

**Example Use Case**: Notifying administrators, updating statistics, or integrating with external systems.

#### `testimonial_approved`

Sent when a testimonial is approved.

**Arguments**:
- `sender`: The testimonial model class
- `instance`: The approved testimonial instance

**Example Use Case**: Notifying the author, updating search indexes, or triggering social media posts.

#### `testimonial_rejected`

Sent when a testimonial is rejected.

**Arguments**:
- `sender`: The testimonial model class
- `instance`: The rejected testimonial instance
- `reason`: The reason for rejection (may be empty)

**Example Use Case**: Notifying the author, logging rejection reasons, or updating moderation statistics.

#### `testimonial_featured`

Sent when a testimonial is featured.

**Arguments**:
- `sender`: The testimonial model class
- `instance`: The featured testimonial instance

**Example Use Case**: Updating the homepage, sending congratulations to the author, or updating featured content caches.

#### `testimonial_archived`

Sent when a testimonial is archived.

**Arguments**:
- `sender`: The testimonial model class
- `instance`: The archived testimonial instance

**Example Use Case**: Cleaning up related resources, updating statistics, or archiving in external systems.

#### `testimonial_responded`

Sent when a response is added to a testimonial.

**Arguments**:
- `sender`: The testimonial model class
- `instance`: The testimonial instance
- `response`: The response text

**Example Use Case**: Notifying the author about the response, updating response statistics, or triggering follow-up workflows.

### Media Signals

#### `testimonial_media_added`

Sent when media is added to a testimonial.

**Arguments**:
- `sender`: The testimonial media model class
- `instance`: The newly created media instance

**Example Use Case**: Processing media files, generating thumbnails, or updating media galleries.

## Connecting to Signals

You can connect to signals in your Django application using the `@receiver` decorator or the `connect` method. Here are examples of both approaches:

### Using the `@receiver` Decorator

```python
from django.dispatch import receiver
from testimonials.signals import testimonial_approved, testimonial_rejected

@receiver(testimonial_approved)
def handle_testimonial_approval(sender, instance, **kwargs):
    """Handle testimonial approval."""
    print(f"Testimonial {instance.id} by {instance.author_name} was approved!")
    
    # Send a thank-you email to the author
    if instance.author_email:
        send_thank_you_email(
            instance.author_email,
            instance.author_name,
            instance.content
        )
    
    # Update statistics
    update_approval_statistics()

@receiver(testimonial_rejected)
def handle_testimonial_rejection(sender, instance, reason, **kwargs):
    """Handle testimonial rejection."""
    print(f"Testimonial {instance.id} was rejected. Reason: {reason}")
    
    # Log the rejection
    log_rejection(instance, reason)
    
    # Send a notification to the author
    if instance.author_email:
        send_rejection_notification(
            instance.author_email,
            instance.author_name,
            reason
        )
```

### Using the `connect` Method

```python
from testimonials.signals import testimonial_created

def handle_new_testimonial(sender, instance, **kwargs):
    """Handle new testimonial creation."""
    print(f"New testimonial created: {instance.id}")
    
    # Notify administrators
    notify_administrators(instance)
    
    # Update testimonial count
    update_testimonial_count()

# Connect the handler to the signal
testimonial_created.connect(handle_new_testimonial)
```

## Signal Handling in a Django App

To use signals effectively in a Django application, it's common to place signal handlers in a `signals.py` file within your app, and then import this file in your app's `apps.py`:

### signals.py

```python
from django.dispatch import receiver
from testimonials.signals import (
    testimonial_created,
    testimonial_approved,
    testimonial_rejected,
    testimonial_featured,
    testimonial_responded
)

@receiver(testimonial_created)
def handle_new_testimonial(sender, instance, **kwargs):
    """Handle new testimonial creation."""
    # Your code here

@receiver(testimonial_approved)
def handle_testimonial_approval(sender, instance, **kwargs):
    """Handle testimonial approval."""
    # Your code here

@receiver(testimonial_rejected)
def handle_testimonial_rejection(sender, instance, reason, **kwargs):
    """Handle testimonial rejection."""
    # Your code here

@receiver(testimonial_featured)
def handle_testimonial_featuring(sender, instance, **kwargs):
    """Handle testimonial featuring."""
    # Your code here

@receiver(testimonial_responded)
def handle_testimonial_response(sender, instance, response, **kwargs):
    """Handle testimonial response."""
    # Your code here
```

### apps.py

```python
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = 'your_app'
    
    def ready(self):
        # Import signal handlers when app is ready
        import your_app.signals
```

## Practical Examples

### Integration with Slack

```python
from django.dispatch import receiver
from testimonials.signals import testimonial_created, testimonial_approved
import requests
import json

@receiver(testimonial_created)
def notify_slack_on_new_testimonial(sender, instance, **kwargs):
    """Send a Slack notification when a new testimonial is created."""
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    message = {
        "text": f"New testimonial received!",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "New Testimonial Received"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*From:*\n{instance.author_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Rating:*\n{'⭐' * instance.rating}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Content:*\n>{instance.content}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Admin"
                        },
                        "url": f"https://yourdomain.com/admin/testimonials/testimonial/{instance.id}/change/"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(message),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Slack notification: {e}")
```

### Integration with Analytics

```python
from django.dispatch import receiver
from testimonials.signals import testimonial_approved, testimonial_rejected
import analytics  # Example analytics library

@receiver(testimonial_approved)
def track_approval_analytics(sender, instance, **kwargs):
    """Track testimonial approvals in analytics."""
    analytics.track(
        event="Testimonial Approved",
        properties={
            "testimonial_id": str(instance.id),
            "author": instance.author_name,
            "rating": instance.rating,
            "category": instance.category.name if instance.category else None,
            "word_count": len(instance.content.split()),
            "has_media": instance.media.exists()
        }
    )

@receiver(testimonial_rejected)
def track_rejection_analytics(sender, instance, reason, **kwargs):
    """Track testimonial rejections in analytics."""
    analytics.track(
        event="Testimonial Rejected",
        properties={
            "testimonial_id": str(instance.id),
            "author": instance.author_name,
            "rating": instance.rating,
            "rejection_reason": reason,
            "word_count": len(instance.content.split())
        }
    )
```

### Email Notifications

```python
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from testimonials.signals import testimonial_responded

@receiver(testimonial_responded)
def send_response_notification(sender, instance, response, **kwargs):
    """Send notification to author when a response is added to their testimonial."""
    if not instance.author_email:
        return
    
    context = {
        "author_name": instance.author_name,
        "testimonial_content": instance.content,
        "response": response,
        "site_name": getattr(settings, 'SITE_NAME', 'Your Website'),
        "testimonial_date": instance.created_at.strftime('%B %d, %Y'),
    }
    
    subject = "We've responded to your testimonial!"
    html_message = render_to_string('emails/response_notification.html', context)
    plain_message = render_to_string('emails/response_notification.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[instance.author_email],
        html_message=html_message,
        fail_silently=False
    )
```

### Social Media Integration

```python
from django.dispatch import receiver
from testimonials.signals import testimonial_featured
import tweepy  # Example Twitter API library

@receiver(testimonial_featured)
def share_featured_testimonial_on_twitter(sender, instance, **kwargs):
    """Share featured testimonials on Twitter."""
    # Skip if no configuration is provided
    if not all([
        getattr(settings, 'TWITTER_API_KEY', None),
        getattr(settings, 'TWITTER_API_SECRET', None),
        getattr(settings, 'TWITTER_ACCESS_TOKEN', None),
        getattr(settings, 'TWITTER_ACCESS_SECRET', None)
    ]):
        return
    
    # Authenticate with Twitter
    auth = tweepy.OAuthHandler(
        settings.TWITTER_API_KEY,
        settings.TWITTER_API_SECRET
    )
    auth.set_access_token(
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_SECRET
    )
    api = tweepy.API(auth)
    
    # Create tweet text
    stars = "★" * instance.rating + "☆" * (5 - instance.rating)
    tweet_text = f"Customer Testimonial: {stars}\n\n"
    
    # Add testimonial content (truncated if needed)
    max_content_length = 200  # Leave room for the rating, attribution, and URL
    content = instance.content
    if len(content) > max_content_length:
        content = content[:max_content_length - 3] + "..."
    tweet_text += f'"{content}"\n\n'
    
    # Add attribution if not anonymous
    if not instance.is_anonymous:
        tweet_text += f"- {instance.author_name}"
        if instance.company:
            tweet_text += f", {instance.company}"
    
    # Add URL if available
    if hasattr(settings, 'TESTIMONIAL_DETAIL_URL_PATTERN'):
        url = settings.TESTIMONIAL_DETAIL_URL_PATTERN.format(id=instance.id, slug=instance.slug)
        tweet_text += f"\n\n{url}"
    
    # Post to Twitter
    try:
        api.update_status(tweet_text)
    except Exception as e:
        print(f"Error posting to Twitter: {e}")
```

### Cache Management

```python
from django.dispatch import receiver
from django.core.cache import cache
from testimonials.signals import (
    testimonial_approved,
    testimonial_featured,
    testimonial_archived
)

@receiver(testimonial_approved)
@receiver(testimonial_featured)
@receiver(testimonial_archived)
def invalidate_testimonial_cache(sender, instance, **kwargs):
    """Invalidate cached testimonial data when status changes."""
    # Clear specific testimonial cache
    cache.delete(f'testimonial:{instance.id}')
    
    # Clear category testimonial list cache
    if instance.category:
        cache.delete(f'testimonial_category:{instance.category.id}')
    
    # Clear featured testimonials cache
    cache.delete('featured_testimonials')
    
    # Clear homepage testimonials cache
    cache.delete('homepage_testimonials')
    
    # Clear testimonial count cache
    cache.delete('testimonial_counts')
```

### Integrating with Search Indexing

```python
from django.dispatch import receiver
from testimonials.signals import (
    testimonial_approved,
    testimonial_featured,
    testimonial_archived,
    testimonial_rejected
)
from .search import update_search_index, remove_from_search_index

@receiver(testimonial_approved)
@receiver(testimonial_featured)
def index_testimonial(sender, instance, **kwargs):
    """Index the testimonial in the search engine."""
    update_search_index(
        index_name='testimonials',
        document_id=str(instance.id),
        document={
            'id': str(instance.id),
            'author': instance.author_name,
            'content': instance.content,
            'rating': instance.rating,
            'status': instance.status,
            'created_at': instance.created_at.isoformat(),
            'category': instance.category.name if instance.category else None,
            'is_featured': instance.status == 'featured',
        }
    )

@receiver(testimonial_archived)
@receiver(testimonial_rejected)
def remove_testimonial_from_index(sender, instance, **kwargs):
    """Remove the testimonial from the search index."""
    remove_from_search_index(
        index_name='testimonials',
        document_id=str(instance.id)
    )
```

## Best Practices

When working with signals, follow these best practices:

1. **Keep Signal Handlers Simple**: Signal handlers should perform specific, focused tasks. If you need complex logic, move it to separate functions.

2. **Handle Exceptions**: Wrap your signal handler code in try-except blocks to prevent exceptions from affecting other signal handlers or the main operation.

3. **Use Async Tasks for Heavy Work**: For time-consuming operations like sending emails or processing media, consider using a task queue like Celery.

4. **Test Signal Handlers**: Write tests for your signal handlers to ensure they work as expected. Use Django's testing framework to send signals and verify the results.

5. **Document Your Signal Handlers**: Add docstrings to your signal handlers explaining what they do, what signals they listen for, and any side effects they have.

6. **Monitor Performance**: Signal handlers can impact performance, especially if they perform database operations or external API calls. Monitor and optimize as needed.

## Common Patterns

### Sending Notifications

```python
@receiver(testimonial_created)
def notify_on_new_testimonial(sender, instance, **kwargs):
    from django.core.mail import mail_managers
    
    subject = f"New testimonial from {instance.author_name}"
    message = f"""
    A new testimonial has been submitted and is awaiting moderation:
    
    Author: {instance.author_name}
    Rating: {instance.rating}/5
    Content: {instance.content}
    
    Review it here: {settings.SITE_URL}/admin/testimonials/testimonial/{instance.id}/change/
    """
    
    mail_managers(subject, message, fail_silently=True)
```

### Logging to External Systems

```python
@receiver(testimonial_rejected)
def log_rejection_to_external_system(sender, instance, reason, **kwargs):
    import logging
    
    external_logger = logging.getLogger('external_system')
    external_logger.info(
        f"TESTIMONIAL_REJECTED: {instance.id}, {instance.author_name}, "
        f"Rating: {instance.rating}, Reason: {reason}"
    )
```

### Updating Related Models

```python
@receiver(testimonial_approved)
def update_author_reputation(sender, instance, **kwargs):
    """Update the author's reputation score when their testimonial is approved."""
    if instance.author:
        author_profile = instance.author.profile
        author_profile.reputation_score += instance.rating
        author_profile.approved_testimonials_count += 1
        author_profile.save(update_fields=['reputation_score', 'approved_testimonials_count'])
```

## Custom Signals

You can also create custom signals for specific needs:

```python
from django.dispatch import Signal

# Define custom signals
testimonial_viewed = Signal()  # Provides sender, instance, user

# Send the signal
def view_testimonial(request, testimonial_id):
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    # ... view logic ...
    
    # Send the signal
    testimonial_viewed.send(
        sender=Testimonial,
        instance=testimonial,
        user=request.user if request.user.is_authenticated else None
    )
    
    # ... rest of view logic ...

# Connect to the custom signal
@receiver(testimonial_viewed)
def track_testimonial_views(sender, instance, user, **kwargs):
    """Track testimonial views for analytics."""
    TestimonialView.objects.create(
        testimonial=instance,
        user=user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
```

## Conclusion

The signal system in Django Testimonials provides a powerful way to extend functionality without modifying the core code. By connecting to these signals, you can integrate testimonials with other systems, implement custom workflows, and enhance the user experience.

For more information on Django signals in general, refer to the [Django documentation on signals](https://docs.djangoproject.com/en/stable/topics/signals/).