# Django Testimonials

[![PyPI version](https://badge.fury.io/py/django-testimonials.svg)](https://badge.fury.io/py/django-testimonials)
[![Build Status](https://github.com/NzeStan/django-testimonials/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/django-testimonials/actions)
[![Documentation Status](https://readthedocs.org/projects/django-testimonials/badge/?version=latest)](https://django-testimonials.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/yourusername/django-testimonials/badge.svg?branch=main)](https://coveralls.io/github/yourusername/django-testimonials?branch=main)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, reusable Django package for managing testimonials in Django projects. Built with Django REST Framework for seamless API integration.

## Features

- **Complete Testimonial Management**: Create, read, update, and delete testimonials with ease
- **Customizable Models**: Use UUID or traditional IDs, extend models for your specific needs
- **Django REST Framework Integration**: Ready-to-use API endpoints
- **Comprehensive Admin Interface**: Sophisticated admin panel for testimonial management
- **Signals and Hooks**: Built-in signals for testimonial lifecycle events
- **Internationalization Ready**: All user-facing strings use `gettext_lazy`
- **Extensive Test Coverage**: Well-tested codebase with comprehensive test suite
- **Detailed Documentation**: Clear, concise documentation with examples

## Requirements
- Python 3.8+
- Django 3.2+
- Django REST Framework 3.12+
- Pillow (for image handling)
- django-filter>=2.4.0

## Quick Start

### Installation

```bash
pip install django-testimonials
```

### Configuration

1. Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'django_filters',
    'testimonials',
]
```

2. Run migrations:

```bash
python manage.py migrate testimonials
```

3. Include the testimonials URLconf in your project's `urls.py`:

```python
urlpatterns = [
    # ... other patterns
    path('api/testimonials/', include('testimonials.api.urls')),
]
```

### Basic Usage

```python
from testimonials.models import Testimonial

# Create a testimonial
testimonial = Testimonial.objects.create(
    author_name="John Doe",
    content="This is an amazing product!",
    rating=5,
    status=Testimonial.Status.PUBLISHED
)

# Get all published testimonials
published_testimonials = Testimonial.objects.published()
```

## Customization

Django Testimonials is designed to be highly customizable. See the [documentation](https://django-testimonials.readthedocs.io/) for details on how to:

- Use UUID instead of traditional IDs
- Extend the base models
- Customize the admin interface
- Configure signal handlers
- And much more!

## Documentation

Complete documentation is available at [https://django-testimonials.readthedocs.io/](https://django-testimonials.readthedocs.io/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.