# testimonials/services/cache_service.py

"""
Centralized cache management service with semantic timeout handling.
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
    DASHBOARD_ANALYTICS = 'testimonials:dashboard:analytics'


class CacheTimeoutType:
    """
    Semantic timeout types for different cache scenarios.
    Maps cache usage patterns to appropriate timeout durations.
    """
    
    # Volatile data that changes frequently
    VOLATILE = 'short'  # 5 minutes
    
    # Standard caching for general data
    STANDARD = 'default'  # 15 minutes
    
    # Statistics and analytics
    STATS = 'stats'  # 30 minutes
    
    # Stable data that rarely changes
    STABLE = 'long'  # 1 hour
    
    # Featured content
    FEATURED = 'featured'  # 2 hours


class TestimonialCacheService:
    """
    Centralized cache management for testimonials with semantic timeout handling.
    """
    
    patterns = CacheKeyPatterns
    timeout_types = CacheTimeoutType
    
    # Map timeout types to settings properties
    _TIMEOUT_MAP = {
        CacheTimeoutType.VOLATILE: 'CACHE_TIMEOUT_SHORT',
        CacheTimeoutType.STANDARD: 'CACHE_TIMEOUT',
        CacheTimeoutType.STATS: 'CACHE_TIMEOUT_STATS',
        CacheTimeoutType.STABLE: 'CACHE_TIMEOUT_LONG',
        CacheTimeoutType.FEATURED: 'CACHE_TIMEOUT_FEATURED',
    }
    
    @classmethod
    def is_enabled(cls):
        """Check if Redis cache is enabled."""
        return app_settings.USE_REDIS_CACHE
    
    @classmethod
    def get_timeout(cls, timeout=None, timeout_type=None):
        """
        Get cache timeout with flexible input options.
        
        Args:
            timeout: Explicit timeout in seconds (highest priority)
            timeout_type: Semantic timeout type (e.g., 'short', 'long', 'stats')
            
        Returns:
            Timeout in seconds
            
        Examples:
            # Explicit timeout (highest priority)
            get_timeout(timeout=3600)  # Returns 3600
            
            # Semantic type
            get_timeout(timeout_type='stats')  # Returns CACHE_TIMEOUT_STATS
            
            # Default
            get_timeout()  # Returns CACHE_TIMEOUT
        """
        # Priority 1: Explicit timeout
        if timeout is not None:
            return timeout
        
        # Priority 2: Semantic timeout type
        if timeout_type:
            setting_name = cls._TIMEOUT_MAP.get(timeout_type, 'CACHE_TIMEOUT')
            return getattr(app_settings, setting_name)
        
        # Priority 3: Default timeout
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
            # ✅ ALWAYS format - this validates required placeholders
            return pattern.format(**kwargs)
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
    def set(cls, key, value, timeout=None, timeout_type=None):
        """
        Set value in cache with flexible timeout options.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Explicit timeout in seconds
            timeout_type: Semantic timeout type ('short', 'long', 'stats', etc.)
            
        Returns:
            True if successful, False otherwise
            
        Examples:
            # Use default timeout
            set('my_key', data)
            
            # Explicit timeout
            set('my_key', data, timeout=3600)
            
            # Semantic timeout
            set('my_key', data, timeout_type='stats')
        """
        if not cls.is_enabled():
            return False
        
        actual_timeout = cls.get_timeout(timeout, timeout_type)
        
        try:
            cache.set(key, value, actual_timeout)
            logger.debug(f"Cached '{key}' for {actual_timeout}s")
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
    def get_or_set(cls, key, callable_func, timeout=None, timeout_type=None):
        """
        Get from cache or compute and set if not exists.
        
        Args:
            key: Cache key
            callable_func: Function to call if cache miss
            timeout: Explicit timeout in seconds
            timeout_type: Semantic timeout type
            
        Returns:
            Cached or computed value
            
        Examples:
            # Use default timeout
            data = get_or_set('key', compute_data)
            
            # Use stats timeout
            stats = get_or_set('stats', compute_stats, timeout_type='stats')
            
            # Use custom timeout
            featured = get_or_set('featured', get_featured, timeout=7200)
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
            cls.set(key, value, timeout, timeout_type)
            return value
        except Exception as e:
            logger.error(f"Error computing value for cache key '{key}': {e}")
            return None
    
    # === SEMANTIC HELPER METHODS ===
    
    @classmethod
    def cache_testimonial(cls, testimonial_id, data, timeout=None):
        """
        Cache a single testimonial with appropriate timeout.
        
        Args:
            testimonial_id: Testimonial ID
            data: Testimonial data to cache
            timeout: Optional custom timeout
        """
        key = cls.get_key('TESTIMONIAL', id=testimonial_id)
        return cls.set(key, data, timeout=timeout, timeout_type='stable')
    
    @classmethod
    def cache_stats(cls, data, timeout=None):
        """
        Cache statistics with appropriate timeout.
        
        Args:
            data: Statistics data to cache
            timeout: Optional custom timeout
        """
        key = cls.get_key('STATS')
        return cls.set(key, data, timeout=timeout, timeout_type='stats')
    
    @classmethod
    def cache_featured(cls, data, timeout=None):
        """
        Cache featured testimonials with appropriate timeout.
        
        Args:
            data: Featured testimonials data
            timeout: Optional custom timeout
        """
        key = cls.get_key('FEATURED')
        return cls.set(key, data, timeout=timeout, timeout_type='featured')
    
    @classmethod
    def cache_dashboard_data(cls, data_type, data, timeout=None):
        """
        Cache dashboard data with short timeout (volatile).
        
        Args:
            data_type: Type of dashboard data ('overview', 'charts', 'analytics')
            data: Dashboard data to cache
            timeout: Optional custom timeout
        """
        pattern_map = {
            'overview': 'DASHBOARD_OVERVIEW',
            'charts': 'DASHBOARD_CHARTS',
            'analytics': 'DASHBOARD_ANALYTICS',
        }
        
        pattern_name = pattern_map.get(data_type, 'DASHBOARD_OVERVIEW')
        key = cls.get_key(pattern_name)
        return cls.set(key, data, timeout=timeout, timeout_type='volatile')
    
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
            cls.get_key('DASHBOARD_ANALYTICS'),
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
    def invalidate_dashboard(cls):
        """Invalidate all dashboard caches."""
        if not cls.is_enabled():
            return
        
        keys_to_delete = [
            cls.get_key('DASHBOARD_OVERVIEW'),
            cls.get_key('DASHBOARD_CHARTS'),
            cls.get_key('DASHBOARD_ANALYTICS'),
        ]
        
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
                cls.get_key('DASHBOARD_ANALYTICS'),
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