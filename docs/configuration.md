# Configuration Guide

Django Testimonials can be configured to fit your specific requirements through various settings in your Django settings file. This guide details all available configuration options.

## Available Settings

All settings are prefixed with `TESTIMONIALS_` and have sensible defaults.

### Core Settings

#### `TESTIMONIALS_USE_UUID`

- **Default**: `False`
- **Type**: Boolean
- **Description**: If `True`, UUIDs will be used as primary keys for all testimonial models instead of auto-incrementing IDs. This can be useful for security and scalability.

```python
# Use UUIDs instead of sequential IDs
TESTIMONIALS_USE_UUID = True
```

#### `TESTIMONIALS_MAX_RATING`

- **Default**: `5`
- **Type**: Integer
- **Description**: Maximum rating value for testimonials. The default is 5 (for a 5-star rating system), but you can change it to any positive integer.

```python
# Use a 10-point rating scale
TESTIMONIALS_MAX_RATING = 10
```

#### `TESTIMONIALS_REQUIRE_APPROVAL`

- **Default**: `True`
- **Type**: Boolean
- **Description**: If `True`, new testimonials will be created with a "pending" status and require manual approval. If `False`, they will be automatically set to "approved".

```python
# Automatically approve all testimonials (not recommended for public sites)
TESTIMONIALS_REQUIRE_APPROVAL = False
```

#### `TESTIMONIALS_ALLOW_ANONYMOUS`

- **Default**: `False`
- **Type**: Boolean
- **Description**: If `True`, users can submit testimonials anonymously. If `False`, anonymous testimonials are not allowed.

```python
# Allow anonymous testimonials
TESTIMONIALS_ALLOW_ANONYMOUS = True
```

### User and Permission Settings

#### `TESTIMONIALS_USER_MODEL`

- **Default**: `settings.AUTH_USER_MODEL`
- **Type**: String
- **Description**: The user model to use for testimonial authors. Defaults to Django's configured user model.

```python
# Use a custom user model
TESTIMONIALS_USER_MODEL = 'myapp.CustomUser'
```

#### `TESTIMONIALS_MODERATION_ROLES`

- **Default**: `[]` (empty list)
- **Type**: List of strings
- **Description**: List of group names that can moderate testimonials. Users in these groups will have permission to approve, reject, feature, and archive testimonials, even if they're not staff or superusers.

```python
# Allow users in the 'content_managers' and 'testimonial_moderators' groups to moderate testimonials
TESTIMONIALS_MODERATION_ROLES = ['content_managers', 'testimonial_moderators']
```

### Feature Settings

#### `TESTIMONIALS_ENABLE_CATEGORIES`

- **Default**: `True`
- **Type**: Boolean
- **Description**: If `True`, categorization of testimonials is enabled. If `False`, the category field will be hidden.

```python
# Disable categories
TESTIMONIALS_ENABLE_CATEGORIES = False
```

#### `TESTIMONIALS_ENABLE_MEDIA`

- **Default**: `True`
- **Type**: Boolean
- **Description**: If `True`, media attachments for testimonials are enabled. If `False`, the media functionality will be disabled.

```python
# Disable media attachments
TESTIMONIALS_ENABLE_MEDIA = False
```

#### `TESTIMONIALS_MEDIA_UPLOAD_PATH`

- **Default**: `"media_testimonials/media/"`
- **Type**: String
- **Description**: Path to upload testimonial media files, relative to your media root.

```python
# Set a custom upload path
TESTIMONIALS_MEDIA_UPLOAD_PATH = "uploads/customer_testimonials/"
```

### Notification Settings

#### `TESTIMONIALS_NOTIFICATION_EMAIL`

- **Default**: `None`
- **Type**: String or None
- **Description**: Email address to send testimonial notifications to. If set, notifications will be sent when new testimonials are created.

```python
# Send notifications to this email
TESTIMONIALS_NOTIFICATION_EMAIL = "testimonials@example.com"
```

### Display Settings

#### `TESTIMONIALS_PAGINATION_SIZE`

- **Default**: `10`
- **Type**: Integer
- **Description**: Default pagination size for testimonial listings in the API.

```python
# Show 20 testimonials per page
TESTIMONIALS_PAGINATION_SIZE = 20
```

### Advanced Settings

#### `TESTIMONIALS_CUSTOM_MODEL`

- **Default**: `None`
- **Type**: String or None
- **Description**: Custom model to use instead of the default Testimonial model. If set, this model will be used for all testimonial operations.

```python
# Use a custom testimonial model
TESTIMONIALS_CUSTOM_MODEL = 'myapp.CustomTestimonial'
```

#### `TESTIMONIALS_CUSTOM_STATUSES`

- **Default**: `None`
- **Type**: Tuple or None
- **Description**: Custom statuses for testimonials. If set, these statuses will replace the default statuses.

```python
# Define custom statuses
TESTIMONIALS_CUSTOM_STATUSES = (
    ('awaiting_review', 'Awaiting Review'),
    ('published', 'Published'),
    ('declined', 'Declined'),
    ('highlighted', 'Highlighted'),
    ('hidden', 'Hidden'),
)
```

#### `TESTIMONIALS_ENABLE_DASHBOARD`

- **Default**: `False`
- **Type**: Boolean
- **Description**: If `True`, a separate admin dashboard for testimonials will be enabled at the URL `/testimonials/dashboard/`.

```python
# Enable the testimonial dashboard
TESTIMONIALS_ENABLE_DASHBOARD = True
```

#### `TESTIMONIALS_REQUIRE_PRIVACY_CONSENT`

- **Default**: `False`
- **Type**: Boolean
- **Description**: If `True`, users will be required to consent to the privacy policy when submitting testimonials.

```python
# Require privacy consent
TESTIMONIALS_REQUIRE_PRIVACY_CONSENT = True
```

## Example Configuration

Here's a complete example configuration:

```python
# Testimonials Configuration
TESTIMONIALS_USE_UUID = True
TESTIMONIALS_MAX_RATING = 5
TESTIMONIALS_REQUIRE_APPROVAL = True
TESTIMONIALS_ALLOW_ANONYMOUS = True
TESTIMONIALS_MODERATION_ROLES = ['content_managers', 'testimonial_moderators']
TESTIMONIALS_ENABLE_CATEGORIES = True
TESTIMONIALS_ENABLE_MEDIA = True
TESTIMONIALS_MEDIA_UPLOAD_PATH = "testimonials/media/"
TESTIMONIALS_NOTIFICATION_EMAIL = "testimonials@example.com"
TESTIMONIALS_PAGINATION_SIZE = 12
TESTIMONIALS_ENABLE_DASHBOARD = True
TESTIMONIALS_REQUIRE_PRIVACY_CONSENT = True
```

## Integration with Django REST Framework Settings

Django Testimonials uses Django REST Framework for its API. You can configure DRF settings to affect the testimonials API behavior:

```python
# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # This will be overridden by TESTIMONIALS_PAGINATION_SIZE for testimonial endpoints
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

## Environment-specific Configuration

You can use different settings for different environments:

```python
# Development settings
if DEBUG:
    TESTIMONIALS_REQUIRE_APPROVAL = False
    TESTIMONIALS_NOTIFICATION_EMAIL = None
else:
    # Production settings
    TESTIMONIALS_REQUIRE_APPROVAL = True
    TESTIMONIALS_NOTIFICATION_EMAIL = "testimonials@example.com"
```

## Next Steps

- Review the [Installation Guide](installation.md) if you haven't installed the package yet
- Check out the [Usage Guide](usage.md) for examples of using Django Testimonials
- Explore the [Customization Guide](customization.md) to learn how to extend the package