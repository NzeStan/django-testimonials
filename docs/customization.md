# Customization Guide

Django Testimonials is designed to be highly customizable to fit different project requirements. This guide covers various ways to customize and extend the package.

## Configuration Options

The simplest way to customize Django Testimonials is through the configuration settings in your Django settings file. See the [Installation Guide](installation.md) for a complete list of available settings.

## Model Customization

### Using UUID Primary Keys

Django Testimonials supports both traditional auto-incrementing IDs and UUIDs as primary keys. To use UUIDs, add this to your settings:

```python
TESTIMONIALS_USE_UUID = True
```

This will automatically use UUIDs for all testimonial models.

### Extending the Base Models

You can create your own models that extend the base models provided by Django Testimonials:

```python
from django.db import models
from testimonials.models.base import BaseModel
from testimonials.models import Testimonial

class ExtendedTestimonial(Testimonial):
    """Custom testimonial model with additional fields."""
    product = models.ForeignKey(
        'yourapp.Product',
        on_delete=models.CASCADE,
        related_name='testimonials'
    )
    purchase_date = models.DateField(null=True, blank=True)
    verified_purchase = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Product Testimonial"
        verbose_name_plural = "Product Testimonials"
```

### Using a Custom Testimonial Model

To use your custom model as the primary testimonial model, add this to your settings:

```python
TESTIMONIALS_CUSTOM_MODEL = 'yourapp.ExtendedTestimonial'
```

## Admin Customization

### Custom Admin Classes

You can extend the provided admin classes to customize the admin interface:

```python
from django.contrib import admin
from testimonials.admin import TestimonialAdmin
from .models import ExtendedTestimonial

@admin.register(ExtendedTestimonial)
class ExtendedTestimonialAdmin(TestimonialAdmin):
    """Custom admin for the extended testimonial model."""
    
    # Add the custom fields to the fieldsets
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        
        # Add a new fieldset for the custom fields
        fieldsets += (
            ('Product Information', {
                'fields': ('product', 'purchase_date', 'verified_purchase')
            }),
        )
        
        return fieldsets
    
    # Add custom fields to list display
    list_display = TestimonialAdmin.list_display + ('product', 'verified_purchase')
    
    # Add custom filters
    list_filter = TestimonialAdmin.list_filter + ('verified_purchase', 'product')
    
    # Custom actions
    actions = TestimonialAdmin.actions + ['mark_as_verified']
    
    def mark_as_verified(self, request, queryset):
        """Mark selected testimonials as verified purchases."""
        updated = queryset.update(verified_purchase=True)
        self.message_user(request, f"{updated} testimonials marked as verified purchases.")
    mark_as_verified.short_description = "Mark selected testimonials as verified purchases"
```

### Custom Admin Templates

You can override the admin templates by creating templates with the same name in your project's template directory:

1. Create a directory structure: `templates/admin/testimonials/`
2. Create template files with the same names as the originals, for example:
   - `templates/admin/testimonials/testimonial/change_form.html`
   - `templates/admin/testimonials/dashboard.html`

## Form Customization

### Custom Forms

You can extend the provided forms to add custom fields or validation:

```python
from django import forms
from testimonials.forms import TestimonialForm
from .models import ExtendedTestimonial, Product

class ProductTestimonialForm(TestimonialForm):
    """Custom form for product testimonials."""
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(active=True),
        required=True,
        label="Product"
    )
    
    purchase_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Purchase Date"
    )
    
    verified_purchase = forms.BooleanField(
        required=False,
        initial=False,
        label="Verified Purchase"
    )
    
    class Meta(TestimonialForm.Meta):
        model = ExtendedTestimonial
        fields = TestimonialForm.Meta.fields + [
            'product', 'purchase_date', 'verified_purchase'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Custom validation logic
        product = cleaned_data.get('product')
        rating = cleaned_data.get('rating')
        
        if product and product.premium and rating < 3:
            self.add_error(
                'rating',
                "Ratings for premium products must be at least 3 stars. Please contact support for issues."
            )
        
        return cleaned_data
```

## API Customization

### Custom Serializers

You can create custom serializers for your extended models:

```python
from rest_framework import serializers
from testimonials.api.serializers import TestimonialSerializer
from .models import ExtendedTestimonial, Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'image']

class ExtendedTestimonialSerializer(TestimonialSerializer):
    """Custom serializer for extended testimonials."""
    
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(active=True),
        source='product',
        write_only=True
    )
    
    class Meta(TestimonialSerializer.Meta):
        model = ExtendedTestimonial
        fields = TestimonialSerializer.Meta.fields + [
            'product', 'product_id', 'purchase_date', 'verified_purchase'
        ]
```

### Custom ViewSets

You can extend the existing viewsets or create your own:

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from testimonials.api.views import TestimonialViewSet
from .models import ExtendedTestimonial
from .serializers import ExtendedTestimonialSerializer

class ProductTestimonialViewSet(TestimonialViewSet):
    """Custom viewset for product testimonials."""
    
    queryset = ExtendedTestimonial.objects.all()
    serializer_class = ExtendedTestimonialSerializer
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get testimonials for a specific product."""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response(
                {"error": "product_id parameter is required"},
                status=400
            )
        
        testimonials = self.get_queryset().filter(product_id=product_id)
        page = self.paginate_queryset(testimonials)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(testimonials, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def verified(self, request):
        """Get only verified purchase testimonials."""
        testimonials = self.get_queryset().filter(verified_purchase=True)
        page = self.paginate_queryset(testimonials)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(testimonials, many=True)
        return Response(serializer.data)
```

### Customizing URL Patterns

You can customize the API URLs by creating your own URL configuration:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from testimonials.api.views import TestimonialCategoryViewSet, TestimonialMediaViewSet
from .api.views import ProductTestimonialViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'product-testimonials', ProductTestimonialViewSet)
router.register(r'categories', TestimonialCategoryViewSet)
router.register(r'media', TestimonialMediaViewSet)

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Template Customization

### Overriding Templates

You can override the built-in templates by creating templates with the same name in your project's template directory:

1. Create a directory structure: `templates/testimonials/`
2. Create template files with the same names as the originals, for example:
   - `templates/testimonials/widgets/star_rating.html`
   - `templates/testimonials/emails/testimonial_approved_subject.txt`
   - `templates/testimonials/emails/testimonial_approved_body.txt`

### Custom Email Templates

To customize email notifications, create your own email templates:

```html
<!-- templates/testimonials/emails/testimonial_approved_body.txt -->
Dear {{ testimonial.author_name }},

Thank you for submitting your testimonial about {{ testimonial.product.name }}!

We're pleased to inform you that your testimonial has been approved and is now published on our website.

Your testimonial:
"{{ testimonial.content }}"

{% if testimonial.verified_purchase %}
We've verified your purchase and marked your testimonial accordingly.
{% endif %}

Thank you for being a valued customer!

Best regards,
{{ site_name }} Team
```

## Signal Handlers

### Custom Signal Handlers

You can connect to the built-in signals to add custom functionality:

```python
from django.dispatch import receiver
from testimonials.signals import testimonial_approved
from .models import ExtendedTestimonial
from .tasks import update_product_rating, notify_product_manager

@receiver(testimonial_approved, sender=ExtendedTestimonial)
def handle_product_testimonial_approval(sender, instance, **kwargs):
    """Handle approval of product testimonials."""
    # Update product average rating
    update_product_rating.delay(instance.product_id)
    
    # Notify product manager for testimonials with low ratings
    if instance.rating <= 2:
        notify_product_manager.delay(
            product_id=instance.product_id,
            testimonial_id=instance.id,
            rating=instance.rating,
            content=instance.content
        )
```

## Permissions and Moderation

### Custom Permission Classes

You can create custom permission classes for the API:

```python
from rest_framework import permissions
from testimonials.api.permissions import CanModerateTestimonial

class IsProductManager(permissions.BasePermission):
    """
    Permission to allow product managers to moderate testimonials for their products.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user is a product manager
        return hasattr(request.user, 'product_manager')
    
    def has_object_permission(self, request, view, obj):
        # Check if this is a product testimonial
        if not hasattr(obj, 'product'):
            return False
        
        # Check if user manages this product
        return (
            hasattr(request.user, 'product_manager') and
            request.user.product_manager.products.filter(id=obj.product.id).exists()
        )
```

### Custom Moderation

You can implement custom moderation logic:

```python
from django.views.generic import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import ExtendedTestimonial

@method_decorator(csrf_exempt, name='dispatch')
class ProductTestimonialModeration(View):
    """Custom moderation view for product testimonials."""
    
    def post(self, request, *args, **kwargs):
        # Check permission
        if not request.user.is_authenticated or not hasattr(request.user, 'product_manager'):
            return JsonResponse({"error": "Permission denied"}, status=403)
        
        # Get testimonial ID and action
        testimonial_id = request.POST.get('testimonial_id')
        action = request.POST.get('action')
        
        if not testimonial_id or not action:
            return JsonResponse({"error": "Missing required parameters"}, status=400)
        
        try:
            testimonial = ExtendedTestimonial.objects.get(id=testimonial_id)
        except ExtendedTestimonial.DoesNotExist:
            return JsonResponse({"error": "Testimonial not found"}, status=404)
        
        # Check if user manages this product
        if not request.user.product_manager.products.filter(id=testimonial.product.id).exists():
            return JsonResponse({"error": "Permission denied"}, status=403)
        
        # Perform action
        if action == 'approve':
            testimonial.approve(user=request.user)
            return JsonResponse({"status": "Testimonial approved"})
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            testimonial.reject(reason=reason, user=request.user)
            return JsonResponse({"status": "Testimonial rejected"})
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)
```

## Advanced Customization

### Custom Managers

You can extend the built-in managers with your own methods:

```python
from django.db import models
from testimonials.managers import TestimonialManager

class ProductTestimonialManager(TestimonialManager):
    """Custom manager for product testimonials."""
    
    def for_product(self, product_id):
        """Get testimonials for a specific product."""
        return self.filter(product_id=product_id)
    
    def high_rated_for_product(self, product_id, min_rating=4):
        """Get high-rated testimonials for a product."""
        return self.for_product(product_id).filter(rating__gte=min_rating)
    
    def recent_for_product(self, product_id, days=30):
        """Get recent testimonials for a product."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.for_product(product_id).filter(created_at__gte=cutoff_date)
    
    def get_product_stats(self, product_id):
        """Get testimonial statistics for a product."""
        from django.db.models import Avg, Count
        
        testimonials = self.for_product(product_id)
        
        return {
            'total': testimonials.count(),
            'average_rating': testimonials.aggregate(Avg('rating'))['rating__avg'] or 0,
            'rating_distribution': {
                i: testimonials.filter(rating=i).count() for i in range(1, 6)
            },
            'verified_count': testimonials.filter(verified_purchase=True).count(),
            'with_media_count': testimonials.filter(media__isnull=False).distinct().count()
        }
```

### Custom Validators

You can create custom validators for testimonials:

```python
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_product_ownership(user, product):
    """Validate that the user has purchased the product."""
    if not user.purchases.filter(product=product).exists():
        raise ValidationError(
            _("You can only leave testimonials for products you've purchased.")
        )

def validate_premium_testimonial(content, product):
    """Validate content length for premium product testimonials."""
    if product.is_premium and len(content) < 50:
        raise ValidationError(
            _("Testimonials for premium products must be at least 50 characters long.")
        )

# Usage in forms
class PremiumProductTestimonialForm(ProductTestimonialForm):
    """Form for premium product testimonials with extra validation."""
    
    def clean(self):
        cleaned_data = super().clean()
        
        product = cleaned_data.get('product')
        content = cleaned_data.get('content')
        user = self.user
        
        if product and user and content:
            # Validate product ownership
            try:
                validate_product_ownership(user, product)
            except ValidationError as e:
                self.add_error('product', e)
            
            # Validate premium content
            try:
                validate_premium_testimonial(content, product)
            except ValidationError as e:
                self.add_error('content', e)
        
        return cleaned_data
```

### Custom Fields

You can create custom fields for your testimonial forms:

```python
from django import forms
from django.utils.translation import gettext_lazy as _

class ProductRatingWidget(forms.Widget):
    """Custom widget for product-specific rating scales."""
    template_name = 'yourapp/widgets/product_rating.html'
    
    def __init__(self, attrs=None, features=None):
        self.features = features or []
        super().__init__(attrs)
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['features'] = self.features
        return context

class ProductRatingField(forms.MultiValueField):
    """Field for rating multiple aspects of a product."""
    
    def __init__(self, features=None, *args, **kwargs):
        self.features = features or [
            ('overall', _('Overall')),
            ('quality', _('Quality')),
            ('value', _('Value for Money')),
            ('usability', _('Ease of Use'))
        ]
        
        fields = [
            forms.IntegerField(
                min_value=1,
                max_value=5,
                required=True
            ) for _ in self.features
        ]
        
        kwargs['widget'] = ProductRatingWidget(features=self.features)
        super().__init__(fields, *args, **kwargs)
    
    def compress(self, data_list):
        """Compress the multiple values into a single value."""
        if not data_list:
            return None
        
        # Return as a dictionary
        return {
            feature[0]: data_list[i] 
            for i, feature in enumerate(self.features)
            if i < len(data_list)
        }
```

### Middleware

You can create middleware to handle testimonial-related tasks:

```python
from django.utils.deprecation import MiddlewareMixin
from .models import ProductView

class ProductTrackingMiddleware(MiddlewareMixin):
    """Middleware to track product views for later testimonial requests."""
    
    def process_response(self, request, response):
        # Only track for authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Check if this is a product detail page
        product_id = request.resolver_match.kwargs.get('product_id')
        if product_id and request.resolver_match.url_name == 'product_detail':
            # Record the product view
            ProductView.objects.create(
                user=request.user,
                product_id=product_id,
                session_id=request.session.session_key
            )
        
        return response
```

### Custom Storage

You can customize how media files are stored:

```python
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

class TestimonialMediaStorage(S3Boto3Storage):
    """Custom storage for testimonial media files."""
    bucket_name = getattr(settings, 'TESTIMONIAL_MEDIA_BUCKET_NAME', 'testimonial-media')
    location = 'testimonials'
    custom_domain = getattr(settings, 'TESTIMONIAL_MEDIA_DOMAIN', None)
    file_overwrite = False
    default_acl = 'public-read'

# Usage in models
class CustomTestimonialMedia(models.Model):
    """Custom testimonial media model with cloud storage."""
    testimonial = models.ForeignKey(
        'yourapp.CustomTestimonial',
        on_delete=models.CASCADE,
        related_name='media'
    )
    file = models.FileField(
        upload_to='media/%Y/%m/%d/',
        storage=TestimonialMediaStorage()
    )
    # ... other fields
```

## Integration with Other Django Apps

### Integration with Django CMS

```python
from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import gettext_lazy as _

@apphook_pool.register
class TestimonialsApphook(CMSApp):
    name = _("Testimonials")
    app_name = 'testimonials'
    
    def get_urls(self, page=None, language=None, **kwargs):
        return ["testimonials.urls"]
```

### Integration with Wagtail

```python
from wagtail.core import blocks
from wagtail.core.models import Page
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.core.fields import StreamField
from testimonials.models import Testimonial

class TestimonialBlock(blocks.StructBlock):
    """Wagtail StreamField block for testimonials."""
    testimonial = blocks.PageChooserBlock(
        required=True,
        page_type='testimonials.TestimonialPage'
    )
    show_rating = blocks.BooleanBlock(default=True, required=False)
    show_author_info = blocks.BooleanBlock(default=True, required=False)
    
    class Meta:
        template = 'testimonials/blocks/testimonial_block.html'
        icon = 'openquote'
        label = 'Testimonial'

class TestimonialCarouselBlock(blocks.StructBlock):
    """Wagtail StreamField block for testimonial carousels."""
    title = blocks.CharBlock(required=False)
    testimonials = blocks.ListBlock(
        blocks.PageChooserBlock(page_type='testimonials.TestimonialPage')
    )
    show_rating = blocks.BooleanBlock(default=True, required=False)
    show_navigation = blocks.BooleanBlock(default=True, required=False)
    
    class Meta:
        template = 'testimonials/blocks/testimonial_carousel_block.html'
        icon = 'list-ul'
        label = 'Testimonial Carousel'

class ContentPage(Page):
    """Content page with testimonial blocks."""
    body = StreamField([
        ('heading', blocks.CharBlock()),
        ('paragraph', blocks.RichTextBlock()),
        ('testimonial', TestimonialBlock()),
        ('testimonial_carousel', TestimonialCarouselBlock()),
        # ... other block types
    ])
    
    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]
```

### Integration with Django REST Framework Authentication

```python
from rest_framework.authentication import TokenAuthentication
from testimonials.api.views import TestimonialViewSet

# Extend the viewset to use token authentication
class CustomTestimonialViewSet(TestimonialViewSet):
    """Custom viewset with token authentication."""
    authentication_classes = [TokenAuthentication]
    
    def perform_create(self, serializer):
        """Associate the testimonial with the authenticated user."""
        serializer.save(author=self.request.user)
```

## What's Next

- Review the [API documentation](api.md) to understand all available endpoints
- Check out the [Signals documentation](signals.md) for more details on the signal system
- See [best practices](best_practices.md) for using Django Testimonials in production
        page = self.paginate_queryset(testimonials)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(testimonials, many=True)
        return Response(serializer.data)
```

### Customizing URL Patterns

You can customize the API URLs by creating your own URL configuration:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from testimonials.api.views import TestimonialCategoryViewSet, TestimonialMediaViewSet
from .api.views import ProductTestimonialViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'product-testimonials', ProductTestimonialViewSet)
router.register(r'categories', TestimonialCategoryViewSet)
router.register(r'media', TestimonialMediaViewSet)

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Template Customization

### Overriding Templates

You can override the built-in templates by creating templates with the same name in your project's template directory:

1. Create a directory structure: `templates/testimonials/`
2. Create template files with the same names as the originals, for example:
   - `templates/testimonials/widgets/star_rating.html`
   - `templates/testimonials/emails/testimonial_approved_subject.txt`
   - `templates/testimonials/emails/testimonial_approved_body.txt`

### Custom Email Templates

To customize email notifications, create your own email templates:

```html
<!-- templates/testimonials/emails/testimonial_approved_body.txt -->
Dear {{ testimonial.author_name }},

Thank you for submitting your testimonial about {{ testimonial.product.name }}!

We're pleased to inform you that your testimonial has been approved and is now published on our website.

Your testimonial:
"{{ testimonial.content }}"

{% if testimonial.verified_purchase %}
We've verified your purchase and marked your testimonial accordingly.
{% endif %}

Thank you for being a valued customer!

Best regards,
{{ site_name }} Team
```

## Signal Handlers

### Custom Signal Handlers

You can connect to the built-in signals to add custom functionality:

```python
from django.dispatch import receiver
from testimonials.signals import testimonial_approved
from .models import ExtendedTestimonial
from .tasks import update_product_rating, notify_product_manager

@receiver(testimonial_approved, sender=ExtendedTestimonial)
def handle_product_testimonial_approval(sender, instance, **kwargs):
    """Handle approval of product testimonials."""
    # Update product average rating
    update_product_rating.delay(instance.product_id)
    
    # Notify product manager for testimonials with low ratings
    if instance.rating <= 2:
        notify_product_manager.delay(
            product_id=instance.product_id,
            testimonial_id=instance.id,
            rating=instance.rating,
            content=instance.content
        )
```

## Permissions and Moderation

### Custom Permission Classes

You can create custom permission classes for the API:

```python
from rest_framework import permissions
from testimonials.api.permissions import CanModerateTestimonial

class IsProductManager(permissions.BasePermission):
    """
    Permission to allow product managers to moderate testimonials for their products.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user is a product manager
        return hasattr(request.user, 'product_manager')
    
    def has_object_permission(self, request, view, obj):
        # Check if this is a product testimonial
        if not hasattr(obj, 'product'):
            return False
        
        # Check if user manages this product
        return (
            hasattr(request.user, 'product_manager') and
            request.user.product_manager.products.filter(id=obj.product.id).exists()
        )
```

### Custom Moderation

You can implement custom moderation logic:

```python
from django.views.generic import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import ExtendedTestimonial

@method_decorator(csrf_exempt, name='dispatch')
class ProductTestimonialModeration(View):
    """Custom moderation view for product testimonials."""
    
    def post(self, request, *args, **kwargs):
        # Check permission
        if not request.user.is_authenticated or not hasattr(request.user, 'product_manager'):
            return JsonResponse({"error": "Permission denied"}, status=403)
        
        # Get testimonial ID and action
        testimonial_id = request.POST.get('testimonial_id')
        action = request.POST.get('action')
        
        if not testimonial_id or not action:
            return JsonResponse({"error": "Missing required parameters"}, status=400)
        
        try:
            testimonial = ExtendedTestimonial.objects.get(id=testimonial_id)
        except ExtendedTestimonial.DoesNotExist:
            return JsonResponse({"error": "Testimonial not found"}, status=404)
        
        # Check if user manages this product
        if not request.user.product_manager.products.filter(id=testimonial.product.id).exists():
            return JsonResponse({"error": "Permission denied"}, status=403)
        
        # Perform action
        if action == 'approve':
            testimonial.approve(user=request.user)
            return JsonResponse({"status": "Testimonial approved"})
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            testimonial.reject(reason=reason, user=request.user)
            return JsonResponse({"status": "Testimonial rejected"})
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)
```

## Advanced Customization

### Custom Managers

You can extend the built-in managers with your own methods:

```python
from django.db import models
from testimonials.managers import TestimonialManager

class ProductTestimonialManager(TestimonialManager):
    """Custom manager for product testimonials."""
    
    def for_product(self, product_id):
        """Get testimonials for a specific product."""
        return self.filter(product_id=product_id)
    
    def high_rated_for_product(self, product_id, min_rating=4):
        """Get high-rated testimonials for a product."""
        return self.for_product(product_id).filter(rating__gte=min_rating)
    
    def recent_for_product(self, product_id, days=30):
        """Get recent testimonials for a product."""
        from django.utils import timezone
        from datetime import timedelta