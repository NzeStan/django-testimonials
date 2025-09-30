import logging
import uuid
import os
from io import BytesIO
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.core.files.base import ContentFile
from .conf import app_settings
from .constants import TestimonialMediaType
import logging
# Set up logging
logger = logging.getLogger("testimonials")


# === CACHE UTILITIES ===

def get_cache_key(key_type, *args):
    """
    Generate a consistent cache key with prefix.
    
    Args:
        key_type: Type of cache key (e.g., 'testimonial', 'category', 'stats')
        *args: Additional key components
    
    Returns:
        String cache key
    """
    prefix = app_settings.CACHE_KEY_PREFIX
    key_parts = [prefix, key_type] + [str(arg) for arg in args]
    return ':'.join(key_parts)


def cache_get_or_set(key, callable_func, timeout=None, version=None):
    """
    Get from cache or set with callable if Redis cache is enabled.
    Falls back to direct callable execution if caching is disabled.
    
    Args:
        key: Cache key
        callable_func: Function to call if cache miss
        timeout: Cache timeout in seconds
        version: Cache version
    
    Returns:
        Cached or computed value
    """
    if not app_settings.USE_REDIS_CACHE:
        return callable_func()
    
    timeout = timeout or app_settings.CACHE_TIMEOUT
    
    try:
        return cache.get_or_set(key, callable_func, timeout, version)
    except Exception as e:
        logger.warning(f"Cache operation failed: {e}, falling back to direct execution")
        return callable_func()


def invalidate_cache_pattern(pattern):
    """
    Invalidate cache keys matching a pattern.
    Only works if Redis cache is enabled.
    
    Args:
        pattern: Cache key pattern (e.g., 'testimonials:category:*')
    """
    if not app_settings.USE_REDIS_CACHE:
        return
    
    try:
        # Try to use Django's cache framework
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(pattern)
        else:
            # Fallback for basic cache backends
            logger.info(f"Cache pattern invalidation not supported, pattern: {pattern}")
    except Exception as e:
        logger.warning(f"Cache pattern invalidation failed: {e}")


def invalidate_testimonial_cache(testimonial_id=None, category_id=None, user_id=None):
    """
    Invalidate testimonial-related cache entries.
    
    Args:
        testimonial_id: Specific testimonial ID
        category_id: Specific category ID  
        user_id: Specific user ID
    """
    if not app_settings.USE_REDIS_CACHE:
        return
    
    cache_keys = []
    
    # General cache keys
    cache_keys.extend([
        get_cache_key('stats'),
        get_cache_key('featured_testimonials'),
        get_cache_key('published_testimonials'),
        get_cache_key('testimonial_counts'),
    ])
    
    # Specific testimonial cache
    if testimonial_id:
        cache_keys.append(get_cache_key('testimonial', testimonial_id))
    
    # Category-specific cache
    if category_id:
        cache_keys.extend([
            get_cache_key('category', category_id),
            get_cache_key('category_testimonials', category_id),
            get_cache_key('category_stats', category_id),
        ])
    
    # User-specific cache
    if user_id:
        cache_keys.extend([
            get_cache_key('user_testimonials', user_id),
            get_cache_key('user_stats', user_id),
        ])
    
    # Delete cache keys
    try:
        cache.delete_many(cache_keys)
        logger.debug(f"Invalidated {len(cache_keys)} cache keys")
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")


# === CELERY TASK UTILITIES ===

def get_celery_app():
    """
    Get the Celery app instance if available.
    
    Returns:
        Celery app or None if not available
    """
    if not app_settings.USE_CELERY:
        return None
    
    try:
        from celery import current_app
        return current_app
    except ImportError:
        logger.warning("Celery not available, falling back to synchronous execution")
        return None


def execute_task(task_func, *args, **kwargs):
    """
    Execute a task either asynchronously (if Celery enabled) or synchronously.
    
    Args:
        task_func: Task function to execute
        *args: Task arguments
        **kwargs: Task keyword arguments
    
    Returns:
        Task result or None for async execution
    """
    celery_app = get_celery_app()
    
    if celery_app and hasattr(task_func, 'delay'):
        try:
            # Execute asynchronously
            return task_func.delay(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Async task execution failed: {e}, falling back to sync")
    
    # Execute synchronously
    try:
        return task_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        return None


# === SLUG UTILITIES ===

def get_unique_slug(model_instance, slug_field, max_length=50):
    """
    Generate a unique slug for a model instance with optimized database queries.

    Args:
        model_instance: The model instance to generate a slug for
        slug_field: The field name to use for creating the slug
        max_length: Maximum length of the slug
    """
    slug_source = getattr(model_instance, slug_field, "")
    if not slug_source:
        # Fallback if source field empty
        slug_source = f"{getattr(model_instance, 'author_name', 'testimonial')}-{timezone.now().timestamp()}"

    slug = slugify(slug_source)[:max_length]
    unique_slug = slug

    model_class = model_instance.__class__
    extension = 1

    # Exclude self on updates and only check slug field for efficiency
    qs = model_class.objects.exclude(pk=model_instance.pk).only('slug')

    # Use exists() for better performance
    while qs.filter(slug=unique_slug).exists():
        extension_str = f"-{extension}"
        unique_slug = f"{slug[:max_length - len(extension_str)]}{extension_str}"
        extension += 1

    return unique_slug


# === FILE HANDLING UTILITIES ===

def generate_upload_path(instance, filename):
    """Generate a unique upload path for testimonial media files."""
    # Sanitize the original filename extension
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if not ext:
        ext = 'bin'  # fallback for files without extension
    
    # Generate a UUID filename
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # Get the testimonial ID and organize by date
    testimonial_id = getattr(instance, "testimonial_id", None)
    date_path = timezone.now().strftime('%Y/%m/%d')
    
    if testimonial_id:
        return os.path.join(
            app_settings.MEDIA_UPLOAD_PATH, 
            date_path,
            str(testimonial_id), 
            unique_filename
        )
    else:
        return os.path.join(
            app_settings.MEDIA_UPLOAD_PATH, 
            date_path,
            "misc", 
            unique_filename
        )

def get_file_type(file_obj):
    """
    Determine the type of a file based on its extension with better categorization.
    
    Args:
        file_obj: File object or file path
        
    Returns:
        str: Media type constant from TestimonialMediaType
        
    Raises:
        ValidationError: If file type is not allowed
    """

    # Get filename
    if hasattr(file_obj, "name"):
        filename = file_obj.name
    else:
        filename = str(file_obj)
    
    # Handle cases where filename might not have an extension
    if '.' not in filename:
        raise ValidationError(_("File must have an extension"))
    
    ext = filename.split('.')[-1].lower()
    
    # Use the allowed extensions from settings
    allowed_extensions = app_settings.ALLOWED_FILE_EXTENSIONS
    
    # Check if extension is allowed first
    if ext not in allowed_extensions:
        raise ValidationError(
            _("File type '%(ext)s' not allowed. Allowed types: %(types)s") % {
                'ext': ext,
                'types': ', '.join(allowed_extensions)
            }
        )
    
    # Define file types by extension
    type_mapping = {
        TestimonialMediaType.IMAGE: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'],
        TestimonialMediaType.VIDEO: ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'mpeg', 'mpg'],
        TestimonialMediaType.AUDIO: ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a', 'wma'],
        TestimonialMediaType.DOCUMENT: ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx'],
    }
    
    # Find matching type
    for media_type, extensions in type_mapping.items():
        if ext in extensions:
            logger.debug(f"Detected media type '{media_type}' for file extension '{ext}'")
            return media_type
    
    # Default to document type for unknown but allowed extensions
    logger.warning(f"Unknown file extension '{ext}' for testimonial media, defaulting to DOCUMENT type")
    return TestimonialMediaType.DOCUMENT

# === THUMBNAIL UTILITIES ===

def generate_thumbnails(image_file, sizes=None):
    """
    Generate thumbnails for an image file.
    
    Args:
        image_file: Image file object
        sizes: Dictionary of size names and dimensions
        
    Returns:
        Dictionary of thumbnail files
    """
    if not app_settings.ENABLE_THUMBNAILS:
        return {}
    
    sizes = sizes or app_settings.THUMBNAIL_SIZES
    thumbnails = {}
    
    try:
        from PIL import Image
        
        # Open the image
        image = Image.open(image_file)
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Generate thumbnails
        for size_name, (width, height) in sizes.items():
            # Create thumbnail
            thumbnail = image.copy()
            thumbnail.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Save to BytesIO
            output = BytesIO()
            thumbnail.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            # Create ContentFile
            thumbnail_file = ContentFile(
                output.getvalue(),
                name=f"thumb_{size_name}_{image_file.name}"
            )
            
            thumbnails[size_name] = thumbnail_file
        
        return thumbnails
        
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        return {}


# === LOGGING UTILITIES ===

def log_testimonial_action(testimonial, action, user=None, notes=None, extra_data=None):
    """
    Log a testimonial action for auditing purposes with structured logging.
    
    Args:
        testimonial: The testimonial instance
        action: The action being performed
        user: The user performing the action
        notes: Any additional notes
        extra_data: Additional structured data
    """
    user_str = f"User: {user.username} (ID: {user.id})" if user else "System"
    testimonial_id = getattr(testimonial, "id", "unknown")
    
    log_data = {
        'action': action,
        'testimonial_id': str(testimonial_id),
        'user': user_str,
        'notes': notes or 'None',
        'timestamp': timezone.now().isoformat(),
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.info(
        f"Testimonial Action: {action} | "
        f"Testimonial ID: {testimonial_id} | "
        f"{user_str} | "
        f"Notes: {notes or 'None'}",
        extra=log_data
    )


# === PERFORMANCE UTILITIES ===

def batch_process(queryset, batch_size=None, callback=None):
    """
    Process queryset in batches for better memory usage.
    
    Args:
        queryset: Django queryset to process
        batch_size: Size of each batch
        callback: Function to call for each batch
        
    Yields:
        Batches of objects
    """
    batch_size = batch_size or app_settings.BULK_OPERATION_BATCH_SIZE
    
    # Use iterator() for memory efficiency
    iterator = queryset.iterator(chunk_size=batch_size)
    batch = []
    
    for item in iterator:
        batch.append(item)
        
        if len(batch) >= batch_size:
            if callback:
                callback(batch)
            yield batch
            batch = []
    
    # Yield remaining items
    if batch:
        if callback:
            callback(batch)
        yield batch


def get_search_query(query):
    """
    Validate and prepare search query with minimum length checking.
    
    Args:
        query: Raw search query string
        
    Returns:
        Cleaned search query or None if invalid
    """
    if not query:
        return None
    
    cleaned_query = query.strip()
    
    if len(cleaned_query) < app_settings.SEARCH_MIN_LENGTH:
        return None
    
    return cleaned_query