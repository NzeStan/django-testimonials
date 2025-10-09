# testimonials/utils.py - REFACTORED

"""
Utility functions for the testimonials app.
Refactored to use services for cache and task management.
"""

import logging
import os
from django.utils import timezone
from django.utils.text import slugify
from .conf import app_settings

logger = logging.getLogger("testimonials")


# === IMPORT SERVICES ===
# Import from services instead of defining here
from .services import TestimonialCacheService, TaskExecutor


# === FILE UTILITIES ===

def generate_upload_path(instance, filename):
    """
    Generate dynamic upload path for media files.
    
    Args:
        instance: Model instance
        filename: Original filename
        
    Returns:
        Upload path string
    """
    from datetime import datetime
    
    # Get file extension
    ext = filename.split('.')[-1] if '.' in filename else 'file'
    
    # Generate path: testimonials/media/YYYY/MM/filename
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    # Clean filename
    base_name = os.path.splitext(filename)[0]
    clean_name = slugify(base_name)[:50]
    
    # Add timestamp to avoid collisions
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    new_filename = f"{clean_name}_{timestamp}.{ext}"
    
    return f'testimonials/media/{year}/{month}/{new_filename}'


def get_file_type(file_obj):
    """
    Detect file type from extension.
    
    Args:
        file_obj: File object
        
    Returns:
        Media type constant
    """
    from .constants import TestimonialMediaType
    
    if not file_obj or not hasattr(file_obj, 'name'):
        return TestimonialMediaType.DOCUMENT
    
    filename = file_obj.name.lower()
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    # Image extensions
    image_exts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp']
    if ext in image_exts:
        return TestimonialMediaType.IMAGE
    
    # Video extensions
    video_exts = ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv']
    if ext in video_exts:
        return TestimonialMediaType.VIDEO
    
    # Audio extensions
    audio_exts = ['mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac']
    if ext in audio_exts:
        return TestimonialMediaType.AUDIO
    
    # Default to document
    return TestimonialMediaType.DOCUMENT


# === SLUG UTILITIES ===

def get_unique_slug(model_instance, slug_field, max_length=50):
    """
    Generate a unique slug for a model instance.
    
    Args:
        model_instance: Model instance
        slug_field: Field name to generate slug from
        max_length: Maximum slug length
        
    Returns:
        Unique slug string
    """
    model_class = model_instance.__class__
    original_slug = slugify(getattr(model_instance, slug_field))[:max_length]
    slug = original_slug
    
    # Check for uniqueness
    counter = 1
    while model_class.objects.filter(slug=slug).exclude(pk=model_instance.pk).exists():
        suffix = f'-{counter}'
        slug = f'{original_slug[:max_length - len(suffix)]}{suffix}'
        counter += 1
    
    return slug


# === LOGGING UTILITIES ===

def log_testimonial_action(testimonial, action, user=None, notes=None, extra_data=None):
    """
    Log testimonial actions for audit trail.
    
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


# === SEARCH UTILITIES ===

def get_search_query(query):
    """
    Validate and prepare search query.
    
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


# === CACHE UTILITIES (BACKWARD COMPATIBLE) ===

def get_cache_key(prefix, *args):
    """
    Generate cache key (backward compatible).
    Now delegates to CacheService.
    
    Args:
        prefix: Key prefix
        *args: Additional key components
        
    Returns:
        Cache key string
    """
    # Map old prefixes to new service patterns
    pattern_map = {
        'testimonial': 'TESTIMONIAL',
        'category': 'CATEGORY',
        'stats': 'STATS',
        'featured_testimonials': 'FEATURED',
        'user_testimonials': 'USER_TESTIMONIALS',
    }
    
    pattern_name = pattern_map.get(prefix, prefix.upper())
    
    # Handle args
    if args:
        if len(args) == 1:
            return TestimonialCacheService.get_key(pattern_name, id=args[0])
        else:
            # Fallback for complex keys
            key_parts = [app_settings.CACHE_KEY_PREFIX, prefix] + [str(arg) for arg in args]
            return ':'.join(key_parts)
    
    return TestimonialCacheService.get_key(pattern_name)


def cache_get_or_set(cache_key, callable_func, timeout=None):
    """
    Get from cache or compute (backward compatible).
    Now delegates to CacheService.
    
    Args:
        cache_key: Cache key
        callable_func: Function to call if cache miss
        timeout: Cache timeout
        
    Returns:
        Cached or computed value
    """
    return TestimonialCacheService.get_or_set(cache_key, callable_func, timeout)


def invalidate_testimonial_cache(testimonial_id=None, category_id=None, user_id=None):
    """
    Invalidate testimonial caches (backward compatible).
    Now delegates to CacheService.
    
    Args:
        testimonial_id: Testimonial ID
        category_id: Category ID
        user_id: User ID
    """
    TestimonialCacheService.invalidate_testimonial(
        testimonial_id=testimonial_id,
        category_id=category_id,
        user_id=user_id
    )


# === TASK UTILITIES (BACKWARD COMPATIBLE) ===

def execute_task(task_func, *args, **kwargs):
    """
    Execute task (backward compatible).
    Now delegates to TaskExecutor.
    
    Args:
        task_func: Task function
        *args: Task arguments
        **kwargs: Task keyword arguments
        
    Returns:
        Task result
    """
    return TaskExecutor.execute(task_func, *args, **kwargs)


# === THUMBNAIL UTILITIES ===

def generate_thumbnails(image_path, sizes=None):
    """
    Generate thumbnails for an image.
    
    Args:
        image_path: Path to original image
        sizes: Dict of size names to dimensions
        
    Returns:
        Dict of thumbnail paths
    """
    if not app_settings.ENABLE_THUMBNAILS:
        return {}
    
    if sizes is None:
        sizes = app_settings.THUMBNAIL_SIZES
    
    thumbnails = {}
    
    try:
        from PIL import Image
        import os
        
        # Open original image
        img = Image.open(image_path)
        
        # Generate each thumbnail
        for size_name, dimensions in sizes.items():
            # Create thumbnail
            thumb = img.copy()
            thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)
            
            # Generate thumbnail path
            base, ext = os.path.splitext(image_path)
            thumb_path = f"{base}_{size_name}{ext}"
            
            # Save thumbnail
            thumb.save(thumb_path, quality=85, optimize=True)
            thumbnails[size_name] = thumb_path
            
            logger.debug(f"Generated {size_name} thumbnail: {thumb_path}")
        
        return thumbnails
    
    except Exception as e:
        logger.error(f"Error generating thumbnails: {e}")
        return {}


# === BATCH PROCESSING ===

def batch_process(queryset, batch_size=None, callback=None):
    """
    Process queryset in batches (backward compatible).
    
    Args:
        queryset: Django queryset
        batch_size: Batch size
        callback: Callback function
        
    Yields:
        Batches of objects
    """
    batch_size = batch_size or app_settings.BULK_OPERATION_BATCH_SIZE
    
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