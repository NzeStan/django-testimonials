# Customization Guide

This guide covers how to extend and customize Django Testimonials to fit your project's needs.

## Custom User Model

Django Testimonials works with any custom user model. It uses `settings.AUTH_USER_MODEL` by default:

```python
# settings.py
AUTH_USER_MODEL = 'accounts.CustomUser'
```

The `Testimonial.author` field is a ForeignKey to whatever user model you configure. No additional setup needed.

## Extending Models

### Adding Custom Fields via Proxy Models

You can create proxy models to add custom methods without modifying the database:

```python
# your_app/models.py
from testimonials.models import Testimonial

class ProjectTestimonial(Testimonial):
    class Meta:
        proxy = True

    def get_display_name(self):
        if self.is_anonymous:
            return "Anonymous"
        return f"{self.author_name} at {self.company}"

    @property
    def is_high_quality(self):
        return self.rating >= 4 and self.is_verified and len(self.content) > 100
```

### Adding Related Models

Create models that relate to testimonials:

```python
# your_app/models.py
from django.db import models
from testimonials.models import Testimonial

class TestimonialVote(models.Model):
    testimonial = models.ForeignKey(
        Testimonial,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    is_helpful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['testimonial', 'user']
```

## Custom Serializers

Override the default serializers to add or modify fields:

```python
# your_app/serializers.py
from testimonials.api.serializers import TestimonialSerializer

class CustomTestimonialSerializer(TestimonialSerializer):
    display_name = serializers.SerializerMethodField()
    vote_count = serializers.SerializerMethodField()

    class Meta(TestimonialSerializer.Meta):
        fields = TestimonialSerializer.Meta.fields + ['display_name', 'vote_count']

    def get_display_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous Customer"
        return obj.author_name

    def get_vote_count(self, obj):
        return getattr(obj, 'vote_count', 0)
```

## Custom ViewSets

Extend the default ViewSet to add custom behavior:

```python
# your_app/views.py
from testimonials.api.views import TestimonialViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

class CustomTestimonialViewSet(TestimonialViewSet):
    serializer_class = CustomTestimonialSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Add vote count annotation
        from django.db.models import Count
        return qs.annotate(vote_count=Count('votes'))

    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        testimonial = self.get_object()
        vote, created = TestimonialVote.objects.get_or_create(
            testimonial=testimonial,
            user=request.user,
            defaults={'is_helpful': True}
        )
        if not created:
            vote.delete()
            return Response({'status': 'vote removed'})
        return Response({'status': 'vote added'})
```

Then wire up your custom viewset:

```python
# your_app/urls.py
from rest_framework.routers import DefaultRouter
from .views import CustomTestimonialViewSet

router = DefaultRouter()
router.register(r'testimonials', CustomTestimonialViewSet)

urlpatterns = router.urls
```

## Custom Permissions

Create custom permission classes:

```python
# your_app/permissions.py
from rest_framework.permissions import BasePermission

class IsVerifiedUser(BasePermission):
    """Only verified users can create testimonials."""

    def has_permission(self, request, view):
        if request.method in ['POST', 'PUT', 'PATCH']:
            return hasattr(request.user, 'is_email_verified') and request.user.is_email_verified
        return True

class CanModerateInCategory(BasePermission):
    """Users can only moderate testimonials in their assigned categories."""

    def has_object_permission(self, request, view, obj):
        if view.action in ['approve', 'reject', 'feature']:
            return obj.category_id in request.user.moderable_category_ids
        return True
```

## Custom Admin

Extend the admin to add custom functionality:

```python
# your_app/admin.py
from testimonials.admin import TestimonialAdmin
from testimonials.models import Testimonial

class CustomTestimonialAdmin(TestimonialAdmin):
    list_display = TestimonialAdmin.list_display + ('vote_count',)

    def vote_count(self, obj):
        return obj.votes.count()
    vote_count.short_description = 'Votes'

# Unregister default and register custom
from django.contrib import admin
admin.site.unregister(Testimonial)
admin.site.register(Testimonial, CustomTestimonialAdmin)
```

## Custom Validators

Add custom validation rules:

```python
# your_app/validators.py
from django.core.exceptions import ValidationError

def validate_business_email(value):
    """Require business email addresses."""
    free_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
    domain = value.split('@')[-1].lower()
    if domain in free_providers:
        raise ValidationError('Please use a business email address.')
```

Apply to the testimonial form:

```python
# your_app/forms.py
from testimonials.forms import TestimonialAdminForm
from .validators import validate_business_email

class CustomTestimonialForm(TestimonialAdminForm):
    def clean_author_email(self):
        email = self.cleaned_data.get('author_email')
        if email:
            validate_business_email(email)
        return email
```

## Custom Signals

Connect to testimonial signals for custom behavior:

```python
# your_app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from testimonials.models import Testimonial

@receiver(post_save, sender=Testimonial)
def on_testimonial_saved(sender, instance, created, **kwargs):
    if created:
        # Send to analytics
        track_new_testimonial(instance)

    if instance.status == 'approved' and not created:
        # Notify marketing team
        notify_marketing_of_approval(instance)
```

Register the signals in your app config:

```python
# your_app/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = 'your_app'

    def ready(self):
        import your_app.signals  # noqa: F401
```

## Custom Templates

Override the built-in dashboard templates by creating templates with the same path in your project's template directory:

```
your_project/
  templates/
    testimonials/
      dashboard/
        overview.html      # Overrides the built-in overview
        analytics.html     # Overrides the built-in analytics
      emails/
        new_testimonial_body.html  # Custom email template
```

Make sure your template directory is listed first in `TEMPLATES`:

```python
# settings.py
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Your templates first
        'APP_DIRS': True,
        # ...
    },
]
```

## Custom Email Templates

Override the email templates to match your brand:

```html
<!-- templates/testimonials/emails/new_testimonial_body.html -->
{% load i18n %}

<div style="font-family: Arial, sans-serif; max-width: 600px;">
    <h2 style="color: #333;">New Testimonial Received</h2>

    <p><strong>From:</strong> {{ testimonial.author_name }}</p>
    <p><strong>Rating:</strong> {{ testimonial.rating }}/{{ max_rating }}</p>
    <p><strong>Content:</strong></p>
    <blockquote style="border-left: 3px solid #007bff; padding-left: 15px;">
        {{ testimonial.content }}
    </blockquote>

    <p>
        <a href="{{ admin_url }}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none;">
            Review in Admin
        </a>
    </p>
</div>
```

## Custom Managers

Extend the default manager for custom query patterns:

```python
# your_app/managers.py
from testimonials.managers import TestimonialManager

class CustomTestimonialManager(TestimonialManager):
    def for_homepage(self):
        """Get testimonials suitable for the homepage."""
        return self.published().filter(
            rating__gte=4,
            is_verified=True,
        ).order_by('-created_at')[:6]

    def by_industry(self, industry):
        """Filter by company industry tag."""
        return self.published().filter(
            extra_data__industry=industry
        )
```
