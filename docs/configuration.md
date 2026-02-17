# Configuration Guide

All settings are optional and have sensible defaults. Override them in your Django `settings.py` as needed.

## Content Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_MIN_CONTENT_LENGTH` | `10` | Minimum testimonial content length |
| `TESTIMONIALS_MAX_CONTENT_LENGTH` | `5000` | Maximum testimonial content length |
| `TESTIMONIALS_MAX_RATING` | `5` | Maximum rating value |
| `TESTIMONIALS_MIN_RATING` | `1` | Minimum rating value |
| `TESTIMONIALS_FORBIDDEN_WORDS` | `[]` | List of words to flag as spam |

```python
# settings.py
TESTIMONIALS_MAX_RATING = 10
TESTIMONIALS_MIN_CONTENT_LENGTH = 20
TESTIMONIALS_FORBIDDEN_WORDS = ["spam", "buy now", "click here"]
```

## Moderation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_REQUIRE_APPROVAL` | `True` | New testimonials start as pending |
| `TESTIMONIALS_ALLOW_ANONYMOUS` | `True` | Allow anonymous submissions |
| `TESTIMONIALS_MODERATION_ROLES` | `[]` | Django group names with moderation rights |
| `TESTIMONIALS_USER_MODEL` | `settings.AUTH_USER_MODEL` | Custom user model reference |

```python
# settings.py
TESTIMONIALS_REQUIRE_APPROVAL = True
TESTIMONIALS_ALLOW_ANONYMOUS = False
TESTIMONIALS_MODERATION_ROLES = ["content_managers", "moderators"]
```

## Feature Toggles

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_ENABLE_CATEGORIES` | `True` | Enable category support |
| `TESTIMONIALS_ENABLE_MEDIA` | `True` | Enable media file attachments |
| `TESTIMONIALS_ENABLE_DASHBOARD` | `False` | Enable the admin dashboard views |
| `TESTIMONIALS_ENABLE_THUMBNAILS` | `True` | Enable thumbnail generation for images |
| `TESTIMONIALS_USE_UUID` | `False` | Use UUID primary keys instead of auto-increment |

```python
# settings.py
TESTIMONIALS_ENABLE_CATEGORIES = True
TESTIMONIALS_ENABLE_MEDIA = True
TESTIMONIALS_ENABLE_DASHBOARD = True
TESTIMONIALS_USE_UUID = False
```

## File Upload Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_MAX_FILE_SIZE` | `10485760` (10MB) | Maximum file upload size in bytes |
| `TESTIMONIALS_MAX_AVATAR_SIZE` | `5242880` (5MB) | Maximum avatar file size in bytes |
| `TESTIMONIALS_MAX_IMAGE_WIDTH` | `2000` | Maximum image width in pixels |
| `TESTIMONIALS_MAX_IMAGE_HEIGHT` | `2000` | Maximum image height in pixels |
| `TESTIMONIALS_ALLOWED_FILE_EXTENSIONS` | `['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mp3', 'wav', 'pdf', 'doc', 'docx']` | Allowed file extensions |
| `TESTIMONIALS_THUMBNAIL_SIZES` | `{'small': (150, 150), 'medium': (300, 300)}` | Thumbnail dimensions |

```python
# settings.py
TESTIMONIALS_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
TESTIMONIALS_ALLOWED_FILE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'mp4']
TESTIMONIALS_THUMBNAIL_SIZES = {
    'small': (100, 100),
    'medium': (300, 300),
    'large': (600, 600),
}
```

## Caching Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_USE_CACHE` | `False` | Enable caching |
| `TESTIMONIALS_CACHE_TIMEOUT` | `900` | Default cache timeout in seconds (15 min) |
| `TESTIMONIALS_CACHE_TIMEOUT_SHORT` | `300` | Short cache timeout (5 min) |
| `TESTIMONIALS_CACHE_TIMEOUT_LONG` | `3600` | Long cache timeout (1 hour) |
| `TESTIMONIALS_CACHE_TIMEOUT_STATS` | `1800` | Statistics cache timeout (30 min) |
| `TESTIMONIALS_CACHE_TIMEOUT_FEATURED` | `7200` | Featured testimonials cache (2 hours) |
| `TESTIMONIALS_CACHE_KEY_PREFIX` | `"testimonials"` | Cache key prefix |

```python
# settings.py
TESTIMONIALS_USE_CACHE = True
TESTIMONIALS_CACHE_TIMEOUT = 900
TESTIMONIALS_CACHE_KEY_PREFIX = "mysite_testimonials"

# Requires a cache backend configured in Django
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'testimonials_cache_table',
    }
}
```

Then run:
```bash
python manage.py createcachetable
```

## Background Task Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_USE_BACKGROUND_TASKS` | `False` | Enable background task processing |
| `TESTIMONIALS_EMAIL_RATE_LIMIT` | `60` | Maximum emails per minute |
| `TESTIMONIALS_BULK_OPERATION_BATCH_SIZE` | `100` | Batch size for bulk operations |

```python
# settings.py
TESTIMONIALS_USE_BACKGROUND_TASKS = True

# Optionally install django-background-tasks for persistent task queue
INSTALLED_APPS += ['background_task']
```

Start the task processor:
```bash
python manage.py process_tasks
```

## Email Notification Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_NOTIFICATION_EMAIL` | `None` | Email address for admin notifications |
| `TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS` | `True` | Send email notifications on new testimonials |
| `TESTIMONIALS_SEND_ADMIN_NOTIFICATIONS` | `True` | Send admin-specific notifications |
| `TESTIMONIALS_USE_HTML_EMAILS` | `True` | Send HTML emails (with plain text fallback) |

```python
# settings.py
TESTIMONIALS_NOTIFICATION_EMAIL = "admin@yoursite.com"
TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS = True
TESTIMONIALS_USE_HTML_EMAILS = True

# Django email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'Your Site <noreply@yoursite.com>'
```

## Search & Pagination Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_PAGINATION_SIZE` | `10` | Default page size for API results |
| `TESTIMONIALS_SEARCH_MIN_LENGTH` | `3` | Minimum search query length |
| `TESTIMONIALS_SEARCH_RESULTS_LIMIT` | `1000` | Maximum search results |

```python
# settings.py
TESTIMONIALS_PAGINATION_SIZE = 20
TESTIMONIALS_SEARCH_MIN_LENGTH = 2
```

## Localization Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TESTIMONIALS_DEFAULT_PHONE_REGION` | `"NG"` | Default phone number region (ISO country code) |

```python
# settings.py
TESTIMONIALS_DEFAULT_PHONE_REGION = "US"
```

## Media Storage

The package uses Django's standard `FileField` and `ImageField`, which means it automatically works with any storage backend you configure:

```python
# Local storage (default)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# AWS S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Google Cloud Storage
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
```

See the [Deployment Guide](deployment.md) for detailed storage backend configuration.

## Full Example Configuration

```python
# settings.py - Production example

INSTALLED_APPS = [
    # ...
    'rest_framework',
    'django_filters',
    'phonenumber_field',
    'testimonials',
]

# Testimonials - Content
TESTIMONIALS_MAX_RATING = 5
TESTIMONIALS_MIN_CONTENT_LENGTH = 20
TESTIMONIALS_MAX_CONTENT_LENGTH = 5000

# Testimonials - Moderation
TESTIMONIALS_REQUIRE_APPROVAL = True
TESTIMONIALS_ALLOW_ANONYMOUS = True
TESTIMONIALS_MODERATION_ROLES = ["content_managers"]

# Testimonials - Features
TESTIMONIALS_ENABLE_CATEGORIES = True
TESTIMONIALS_ENABLE_MEDIA = True
TESTIMONIALS_ENABLE_DASHBOARD = True

# Testimonials - Performance
TESTIMONIALS_USE_CACHE = True
TESTIMONIALS_CACHE_TIMEOUT = 900
TESTIMONIALS_USE_BACKGROUND_TASKS = True

# Testimonials - Notifications
TESTIMONIALS_NOTIFICATION_EMAIL = "admin@yoursite.com"
TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS = True

# Testimonials - Files
TESTIMONIALS_MAX_FILE_SIZE = 10 * 1024 * 1024
TESTIMONIALS_ENABLE_THUMBNAILS = True
```
