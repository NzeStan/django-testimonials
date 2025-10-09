# testimonials/services/cache_service.py

"""
Centralized cache management service.
Eliminates scattered cache key generation and invalidation logic.
"""

import logging
from django.core.cache import cache
from ..conf import app_settings

logger = logging.getLogger("testimonials")


class CacheKeyPatterns:
    """Define all cache key patterns in one place."""
    
    # General patterns
    STATS = 'testimonials:stats'
    FEATURED = 'testimonials:featured'
    PUBLISHED = 'testimonials:published'
    COUNTS = 'testimonials:counts'
    
    # Entity-specific patterns
    TESTIMONIAL = 'testimonials:testimonial:{id}'
    CATEGORY = 'testimonials:category:{id}'
    CATEGORY_TESTIMONIALS = 'testimonials:category:{id}:testimonials'
    CATEGORY_STATS = 'testimonials:category:{id}:stats'
    
    # User-specific patterns
    USER_TESTIMONIALS = 'testimonials:user:{id}:testimonials'
    USER_STATS = 'testimonials:user:{id}:stats'
    
    # Media patterns
    MEDIA = 'testimonials:media:{id}'
    MEDIA_STATS = 'testimonials:media:stats'
    
    # Dashboard patterns
    DASHBOARD_OVERVIEW = 'testimonials:dashboard:overview'
    DASHBOARD_CHARTS = 'testimonials:dashboard:charts'


class TestimonialCacheService:
    """
    Centralized cache management for testimonials.
    Provides consistent cache operations across the application.
    """
    
    patterns = CacheKeyPatterns
    
    @classmethod
    def is_enabled(cls):
        """Check if Redis cache is enabled."""
        return app_settings.USE_REDIS_CACHE
    
    @classmethod
    def get_timeout(cls):
        """Get configured cache timeout."""
        return app_settings.CACHE_TIMEOUT
    
    # === KEY GENERATION ===
    
    @classmethod
    def get_key(cls, pattern_name, **kwargs):
        """
        Generate cache key from pattern name.
        
        Args:
            pattern_name: Name of the pattern (e.g., 'TESTIMONIAL', 'CATEGORY')
            **kwargs: Values to format into the pattern
            
        Returns:
            Formatted cache key or None if pattern not found
            
        Example:
            get_key('TESTIMONIAL', id=123) -> 'testimonials:testimonial:123'
        """
        pattern = getattr(cls.patterns, pattern_name, None)
        if not pattern:
            logger.warning(f"Cache key pattern '{pattern_name}' not found")
            return None
        
        try:
            return pattern.format(**kwargs) if kwargs else pattern
        except KeyError as e:
            logger.error(f"Missing key for pattern {pattern_name}: {e}")
            return None
    
    # === CACHE OPERATIONS ===
    
    @classmethod
    def get(cls, key, default=None):
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        if not cls.is_enabled():
            return default
        
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            return default
    
    @classmethod
    def set(cls, key, value, timeout=None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not cls.is_enabled():
            return False
        
        timeout = timeout or cls.get_timeout()
        
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")
            return False
    
    @classmethod
    def delete(cls, key):
        """
        Delete single cache key.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not cls.is_enabled():
            return False
        
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")
            return False
    
    @classmethod
    def delete_many(cls, keys):
        """
        Delete multiple cache keys.
        
        Args:
            keys: List of cache keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not cls.is_enabled():
            return 0
        
        # Filter out None values
        valid_keys = [k for k in keys if k]
        
        if not valid_keys:
            return 0
        
        try:
            cache.delete_many(valid_keys)
            logger.debug(f"Deleted {len(valid_keys)} cache keys")
            return len(valid_keys)
        except Exception as e:
            logger.warning(f"Cache delete_many failed: {e}")
            return 0
    
    @classmethod
    def get_or_set(cls, key, callable_func, timeout=None):
        """
        Get from cache or compute and set if not exists.
        
        Args:
            key: Cache key
            callable_func: Function to call if cache miss
            timeout: Cache timeout in seconds
            
        Returns:
            Cached or computed value
        """
        if not cls.is_enabled():
            return callable_func()
        
        # Try to get from cache
        value = cls.get(key)
        if value is not None:
            return value
        
        # Compute value
        try:
            value = callable_func()
            cls.set(key, value, timeout)
            return value
        except Exception as e:
            logger.error(f"Error computing value for cache key '{key}': {e}")
            return None
    
    # === INVALIDATION METHODS ===
    
    @classmethod
    def invalidate_testimonial(cls, testimonial_id=None, category_id=None, user_id=None):
        """
        Invalidate testimonial-related caches.
        
        Args:
            testimonial_id: Specific testimonial ID
            category_id: Related category ID
            user_id: Related user ID
        """
        if not cls.is_enabled():
            return
        
        keys_to_delete = [
            cls.get_key('STATS'),
            cls.get_key('FEATURED'),
            cls.get_key('PUBLISHED'),
            cls.get_key('COUNTS'),
            cls.get_key('DASHBOARD_OVERVIEW'),
            cls.get_key('DASHBOARD_CHARTS'),
        ]
        
        # Testimonial-specific cache
        if testimonial_id:
            keys_to_delete.append(cls.get_key('TESTIMONIAL', id=testimonial_id))
        
        # Category-specific cache
        if category_id:
            keys_to_delete.extend([
                cls.get_key('CATEGORY', id=category_id),
                cls.get_key('CATEGORY_TESTIMONIALS', id=category_id),
                cls.get_key('CATEGORY_STATS', id=category_id),
            ])
        
        # User-specific cache
        if user_id:
            keys_to_delete.extend([
                cls.get_key('USER_TESTIMONIALS', id=user_id),
                cls.get_key('USER_STATS', id=user_id),
            ])
        
        cls.delete_many(keys_to_delete)
    
    @classmethod
    def invalidate_category(cls, category_id):
        """
        Invalidate category-related caches.
        
        Args:
            category_id: Category ID
        """
        if not cls.is_enabled():
            return
        
        keys_to_delete = [
            cls.get_key('STATS'),
            cls.get_key('CATEGORY', id=category_id),
            cls.get_key('CATEGORY_TESTIMONIALS', id=category_id),
            cls.get_key('CATEGORY_STATS', id=category_id),
        ]
        
        cls.delete_many(keys_to_delete)
    
    @classmethod
    def invalidate_media(cls, media_id=None, testimonial_id=None):
        """
        Invalidate media-related caches.
        
        Args:
            media_id: Specific media ID
            testimonial_id: Related testimonial ID
        """
        if not cls.is_enabled():
            return
        
        keys_to_delete = [
            cls.get_key('MEDIA_STATS'),
        ]
        
        if media_id:
            keys_to_delete.append(cls.get_key('MEDIA', id=media_id))
        
        if testimonial_id:
            keys_to_delete.append(cls.get_key('TESTIMONIAL', id=testimonial_id))
        
        cls.delete_many(keys_to_delete)
    
    @classmethod
    def invalidate_all(cls):
        """
        Invalidate all testimonial-related caches.
        Use with caution - only for major data changes.
        """
        if not cls.is_enabled():
            return
        
        try:
            # Get all possible general cache keys
            general_keys = [
                cls.get_key('STATS'),
                cls.get_key('FEATURED'),
                cls.get_key('PUBLISHED'),
                cls.get_key('COUNTS'),
                cls.get_key('MEDIA_STATS'),
                cls.get_key('DASHBOARD_OVERVIEW'),
                cls.get_key('DASHBOARD_CHARTS'),
            ]
            
            cls.delete_many(general_keys)
            logger.info("Invalidated all general testimonial caches")
        except Exception as e:
            logger.error(f"Error invalidating all caches: {e}")


# Convenience function for backward compatibility
def invalidate_testimonial_cache(testimonial_id=None, category_id=None, user_id=None):
    """
    Backward compatible function for cache invalidation.
    Delegates to CacheService.
    """
    TestimonialCacheService.invalidate_testimonial(
        testimonial_id=testimonial_id,
        category_id=category_id,
        user_id=user_id
    )