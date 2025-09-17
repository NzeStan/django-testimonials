# Installation Guide

This guide covers the installation and basic setup of the Django Testimonials package.

## Requirements

Django Testimonials requires:

- Python 3.8+
- Django 3.2+
- Django REST Framework 3.12+
- Pillow (for image handling)
- django-phonenumber-field with phonenumbers support
- django-filter 2.4.0+

## Installation

### Via PyPI

The easiest way to install Django Testimonials is from PyPI:

```bash
pip install django-testimonials
```

### From Source

Alternatively, you can install from source:

```bash
git clone https://github.com/yourusername/django-testimonials.git
cd django-testimonials
pip install -e .
```

## Setup

### 1. Add to INSTALLED_APPS

Add 'testimonials' to your `INSTALLED_APPS` in your Django settings file:

```python
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'testimonials',
    'django_filters',
]
```

### 2. Run Migrations

Run the migrations to create the necessary database tables:

```bash
python manage.py migrate testimonials
```

### 3. Include URLs

Include the Django Testimonials URLs in your project's `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other URL patterns
    path('testimonials/', include('testimonials.urls')),
]
```

This will make the API available at `/testimonials/api/`.

### 4. Configure Settings (Optional)

Django Testimonials works out of the box with sensible defaults, but you can customize its behavior by adding settings to your Django settings file. Here are the available settings with their default values:

```python
# Use UUID as primary key instead of auto-incrementing IDs
TESTIMONIALS_USE_UUID = False

# Maximum rating value (default is 5-star rating system)
TESTIMONIALS_MAX_RATING = 5

# Whether testimonials require approval before being published
TESTIMONIALS_REQUIRE_APPROVAL = True

# Whether anonymous testimonials are allowed
TESTIMONIALS_ALLOW_ANONYMOUS = False

# User model to use for testimonial authors (default is AUTH_USER_MODEL)
TESTIMONIALS_USER_MODEL = settings.AUTH_USER_MODEL

# List of roles that can moderate testimonials (e.g., ['testimonial_moderator'])
TESTIMONIALS_MODERATION_ROLES = []

# Whether to enable categorization of testimonials
TESTIMONIALS_ENABLE_CATEGORIES = True

# Whether to enable media attachments for testimonials
TESTIMONIALS_ENABLE_MEDIA = True

# Path to upload testimonial media
TESTIMONIALS_MEDIA_UPLOAD_PATH = "media_testimonials/media/"

# Email address to send testimonial notifications to
TESTIMONIALS_NOTIFICATION_EMAIL = None

# Default pagination size for testimonial listings
TESTIMONIALS_PAGINATION_SIZE = 10

# If you want to use a custom Testimonial model
TESTIMONIALS_CUSTOM_MODEL = None

# Enable a separate admin dashboard for testimonials
TESTIMONIALS_ENABLE_DASHBOARD = False

# Whether to require privacy consent when submitting testimonials
TESTIMONIALS_REQUIRE_PRIVACY_CONSENT = False

```

## Next Steps

After installation, you can:

- [Configure the package](configuration.md) for your specific needs
- Learn about [usage and common patterns](usage.md)
- Check out the [API documentation](api.md)
- Review [customization options](customization.md)