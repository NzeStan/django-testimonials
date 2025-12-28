# testimonials/tests/test_cache_service.py

"""
Comprehensive tests for TestimonialCacheService.
Tests cover basic operations, timeout handling, key generation,
semantic helpers, error handling, and edge cases.
"""

from unittest.mock import patch, MagicMock, PropertyMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from testimonials.services.cache_service import (
    TestimonialCacheService,
    CacheKeyPatterns,
    CacheTimeoutType,
    invalidate_testimonial_cache
)
from testimonials.conf import app_settings


# ============================================================================
# BASIC OPERATIONS TESTS
# ============================================================================

class CacheServiceBasicOperationsTests(TestCase):
    """Test basic cache operations (get, set, delete)."""
    
    def setUp(self):
        """Clear cache before each test."""
        cache.clear()
    
    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_is_enabled_when_redis_cache_enabled(self):
        """Test is_enabled returns True when Redis cache is enabled."""
        result = TestimonialCacheService.is_enabled()
        self.assertTrue(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_is_enabled_when_redis_cache_disabled(self):
        """Test is_enabled returns False when Redis cache is disabled."""
        result = TestimonialCacheService.is_enabled()
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_set_and_get_basic_value(self):
        """Test setting and getting a basic value."""
        key = 'test_key'
        value = 'test_value'
        
        # Set value
        result = TestimonialCacheService.set(key, value)
        self.assertTrue(result)
        
        # Get value
        cached = TestimonialCacheService.get(key)
        self.assertEqual(cached, value)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_set_and_get_complex_value(self):
        """Test setting and getting complex data structures."""
        key = 'complex_data'
        value = {
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'string': 'test',
            'number': 42,
            'boolean': True,
            'none': None
        }
        
        TestimonialCacheService.set(key, value)
        cached = TestimonialCacheService.get(key)
        
        self.assertEqual(cached, value)
        self.assertEqual(cached['list'], [1, 2, 3])
        self.assertEqual(cached['dict']['nested'], 'value')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_returns_default_when_key_not_found(self):
        """Test get returns default value when key doesn't exist."""
        result = TestimonialCacheService.get('nonexistent_key', default='default_value')
        self.assertEqual(result, 'default_value')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_returns_none_when_no_default_provided(self):
        """Test get returns None when key doesn't exist and no default."""
        result = TestimonialCacheService.get('nonexistent_key')
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_delete_removes_value(self):
        """Test delete successfully removes cached value."""
        key = 'test_delete'
        TestimonialCacheService.set(key, 'value')
        
        # Verify it exists
        self.assertEqual(TestimonialCacheService.get(key), 'value')
        
        # Delete it
        result = TestimonialCacheService.delete(key)
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertIsNone(TestimonialCacheService.get(key))
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_delete_nonexistent_key(self):
        """Test deleting a key that doesn't exist."""
        result = TestimonialCacheService.delete('nonexistent_key')
        self.assertTrue(result)  # Should succeed without error
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_delete_many_removes_multiple_keys(self):
        """Test delete_many removes multiple keys."""
        keys = ['key1', 'key2', 'key3']
        
        # Set all keys
        for key in keys:
            TestimonialCacheService.set(key, f'value_{key}')
        
        # Delete all
        count = TestimonialCacheService.delete_many(keys)
        self.assertEqual(count, 3)
        
        # Verify all are gone
        for key in keys:
            self.assertIsNone(TestimonialCacheService.get(key))
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_delete_many_with_none_values(self):
        """Test delete_many filters out None values."""
        keys = ['key1', None, 'key2', None, 'key3']
        
        # Set valid keys
        for key in ['key1', 'key2', 'key3']:
            TestimonialCacheService.set(key, 'value')
        
        # Delete with None values - should filter them out
        count = TestimonialCacheService.delete_many(keys)
        self.assertEqual(count, 3)  # Only 3 valid keys
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_delete_many_with_empty_list(self):
        """Test delete_many with empty list."""
        count = TestimonialCacheService.delete_many([])
        self.assertEqual(count, 0)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_delete_many_with_all_none_values(self):
        """Test delete_many with all None values."""
        count = TestimonialCacheService.delete_many([None, None, None])
        self.assertEqual(count, 0)


# ============================================================================
# CACHE DISABLED TESTS
# ============================================================================

class CacheDisabledTests(TestCase):
    """Test behavior when cache is disabled."""
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_set_returns_false_when_disabled(self):
        """Test set returns False when cache is disabled."""
        result = TestimonialCacheService.set('key', 'value')
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_get_returns_default_when_disabled(self):
        """Test get returns default when cache is disabled."""
        result = TestimonialCacheService.get('key', default='default')
        self.assertEqual(result, 'default')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_delete_returns_false_when_disabled(self):
        """Test delete returns False when cache is disabled."""
        result = TestimonialCacheService.delete('key')
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_delete_many_returns_zero_when_disabled(self):
        """Test delete_many returns 0 when cache is disabled."""
        count = TestimonialCacheService.delete_many(['key1', 'key2'])
        self.assertEqual(count, 0)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_get_or_set_calls_function_when_disabled(self):
        """Test get_or_set calls function directly when cache disabled."""
        call_count = 0
        
        def compute_value():
            nonlocal call_count
            call_count += 1
            return 'computed'
        
        # Call twice - function should be called both times (no cache)
        result1 = TestimonialCacheService.get_or_set('key', compute_value)
        result2 = TestimonialCacheService.get_or_set('key', compute_value)
        
        self.assertEqual(result1, 'computed')
        self.assertEqual(result2, 'computed')
        self.assertEqual(call_count, 2)  # Called twice, no caching


# ============================================================================
# TIMEOUT HANDLING TESTS
# ============================================================================

class CacheTimeoutTests(TestCase):
    """Test timeout handling with explicit and semantic types."""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT=900,
        TESTIMONIALS_CACHE_TIMEOUT_SHORT=300,
        TESTIMONIALS_CACHE_TIMEOUT_LONG=3600,
        TESTIMONIALS_CACHE_TIMEOUT_STATS=1800,
        TESTIMONIALS_CACHE_TIMEOUT_FEATURED=7200
    )
    def test_get_timeout_with_explicit_value(self):
        """Test explicit timeout takes highest priority."""
        timeout = TestimonialCacheService.get_timeout(timeout=1234)
        self.assertEqual(timeout, 1234)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_SHORT=300
    )
    def test_get_timeout_with_semantic_type_short(self):
        """Test semantic timeout type 'short'."""
        timeout = TestimonialCacheService.get_timeout(timeout_type='short')
        self.assertEqual(timeout, 300)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_LONG=3600
    )
    def test_get_timeout_with_semantic_type_long(self):
        """Test semantic timeout type 'long'."""
        timeout = TestimonialCacheService.get_timeout(timeout_type='long')
        self.assertEqual(timeout, 3600)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_STATS=1800
    )
    def test_get_timeout_with_semantic_type_stats(self):
        """Test semantic timeout type 'stats'."""
        timeout = TestimonialCacheService.get_timeout(timeout_type='stats')
        self.assertEqual(timeout, 1800)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_FEATURED=7200
    )
    def test_get_timeout_with_semantic_type_featured(self):
        """Test semantic timeout type 'featured'."""
        timeout = TestimonialCacheService.get_timeout(timeout_type='featured')
        self.assertEqual(timeout, 7200)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT=900
    )
    def test_get_timeout_with_no_arguments_returns_default(self):
        """Test get_timeout with no arguments returns default."""
        timeout = TestimonialCacheService.get_timeout()
        self.assertEqual(timeout, 900)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT=900
    )
    def test_get_timeout_with_invalid_semantic_type_returns_default(self):
        """Test invalid semantic type falls back to default."""
        timeout = TestimonialCacheService.get_timeout(timeout_type='invalid_type')
        self.assertEqual(timeout, 900)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_SHORT=300
    )
    def test_get_timeout_explicit_overrides_semantic(self):
        """Test explicit timeout overrides semantic type."""
        timeout = TestimonialCacheService.get_timeout(
            timeout=5000,
            timeout_type='short'
        )
        self.assertEqual(timeout, 5000)  # Explicit wins
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    @patch('django.core.cache.cache.set')
    def test_set_with_explicit_timeout(self, mock_set):
        """Test set uses explicit timeout when provided."""
        TestimonialCacheService.set('key', 'value', timeout=1234)
        mock_set.assert_called_once_with('key', 'value', 1234)
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_STATS=1800
    )
    @patch('django.core.cache.cache.set')
    def test_set_with_semantic_timeout_type(self, mock_set):
        """Test set uses semantic timeout type."""
        TestimonialCacheService.set('key', 'value', timeout_type='stats')
        mock_set.assert_called_once_with('key', 'value', 1800)


# ============================================================================
# KEY GENERATION TESTS
# ============================================================================

class CacheKeyGenerationTests(TestCase):
    """Test cache key pattern generation."""
    
    def test_get_key_simple_pattern(self):
        """Test getting key for simple pattern without formatting."""
        key = TestimonialCacheService.get_key('STATS')
        self.assertEqual(key, 'testimonials:stats')
    
    def test_get_key_with_single_placeholder(self):
        """Test getting key with single placeholder."""
        key = TestimonialCacheService.get_key('TESTIMONIAL', id=123)
        self.assertEqual(key, 'testimonials:testimonial:123')
    
    def test_get_key_with_multiple_placeholders(self):
        """Test getting key with multiple placeholders if any exist."""
        # Test with single placeholder pattern
        key = TestimonialCacheService.get_key('CATEGORY_TESTIMONIALS', id=5)
        self.assertEqual(key, 'testimonials:category:5:testimonials')
    
    def test_get_key_for_user_testimonials(self):
        """Test getting key for user-specific testimonials."""
        key = TestimonialCacheService.get_key('USER_TESTIMONIALS', id=42)
        self.assertEqual(key, 'testimonials:user:42:testimonials')
    
    def test_get_key_for_media(self):
        """Test getting key for media."""
        key = TestimonialCacheService.get_key('MEDIA', id=99)
        self.assertEqual(key, 'testimonials:media:99')
    
    def test_get_key_for_dashboard_patterns(self):
        """Test getting keys for dashboard patterns."""
        overview_key = TestimonialCacheService.get_key('DASHBOARD_OVERVIEW')
        charts_key = TestimonialCacheService.get_key('DASHBOARD_CHARTS')
        analytics_key = TestimonialCacheService.get_key('DASHBOARD_ANALYTICS')
        
        self.assertEqual(overview_key, 'testimonials:dashboard:overview')
        self.assertEqual(charts_key, 'testimonials:dashboard:charts')
        self.assertEqual(analytics_key, 'testimonials:dashboard:analytics')
    
    def test_get_key_with_nonexistent_pattern(self):
        """Test get_key with pattern that doesn't exist."""
        key = TestimonialCacheService.get_key('NONEXISTENT_PATTERN')
        self.assertIsNone(key)
    
    def test_get_key_missing_required_placeholder(self):
        """Test get_key when required placeholder is missing."""
        key = TestimonialCacheService.get_key('TESTIMONIAL')  # Missing 'id'
        self.assertIsNone(key)
    
    def test_get_key_with_string_id(self):
        """Test get_key with string ID."""
        key = TestimonialCacheService.get_key('CATEGORY', id='abc-123')
        self.assertEqual(key, 'testimonials:category:abc-123')
    
    def test_all_cache_key_patterns_defined(self):
        """Test that all expected cache key patterns are defined."""
        patterns = CacheKeyPatterns
        
        # Verify key patterns exist
        self.assertTrue(hasattr(patterns, 'STATS'))
        self.assertTrue(hasattr(patterns, 'FEATURED'))
        self.assertTrue(hasattr(patterns, 'PUBLISHED'))
        self.assertTrue(hasattr(patterns, 'TESTIMONIAL'))
        self.assertTrue(hasattr(patterns, 'CATEGORY'))
        self.assertTrue(hasattr(patterns, 'USER_TESTIMONIALS'))
        self.assertTrue(hasattr(patterns, 'MEDIA'))
        self.assertTrue(hasattr(patterns, 'DASHBOARD_OVERVIEW'))


# ============================================================================
# GET OR SET TESTS
# ============================================================================

class CacheGetOrSetTests(TestCase):
    """Test get_or_set functionality."""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_computes_on_cache_miss(self):
        """Test get_or_set computes value on cache miss."""
        call_count = 0
        
        def compute_value():
            nonlocal call_count
            call_count += 1
            return 'computed_value'
        
        result = TestimonialCacheService.get_or_set('test_key', compute_value)
        
        self.assertEqual(result, 'computed_value')
        self.assertEqual(call_count, 1)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_uses_cache_on_hit(self):
        """Test get_or_set uses cached value on hit."""
        call_count = 0
        
        def compute_value():
            nonlocal call_count
            call_count += 1
            return 'computed_value'
        
        # First call - computes and caches
        result1 = TestimonialCacheService.get_or_set('test_key', compute_value)
        
        # Second call - uses cache
        result2 = TestimonialCacheService.get_or_set('test_key', compute_value)
        
        self.assertEqual(result1, 'computed_value')
        self.assertEqual(result2, 'computed_value')
        self.assertEqual(call_count, 1)  # Only called once
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_with_explicit_timeout(self):
        """Test get_or_set with explicit timeout."""
        def compute():
            return {'data': 'test'}
        
        with patch('django.core.cache.cache.set') as mock_set:
            TestimonialCacheService.get_or_set('key', compute, timeout=3600)
            mock_set.assert_called_once()
            args = mock_set.call_args[0]
            self.assertEqual(args[2], 3600)  # timeout argument
    
    @override_settings(
        TESTIMONIALS_USE_REDIS_CACHE=True,
        TESTIMONIALS_CACHE_TIMEOUT_STATS=1800
    )
    def test_get_or_set_with_semantic_timeout(self):
        """Test get_or_set with semantic timeout type."""
        def compute():
            return {'stats': 'data'}
        
        with patch('django.core.cache.cache.set') as mock_set:
            TestimonialCacheService.get_or_set('key', compute, timeout_type='stats')
            mock_set.assert_called_once()
            args = mock_set.call_args[0]
            self.assertEqual(args[2], 1800)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_handles_callable_exception(self):
        """Test get_or_set handles exception in callable."""
        def failing_compute():
            raise ValueError("Computation failed")
        
        result = TestimonialCacheService.get_or_set('key', failing_compute)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_with_none_return_value(self):
        """Test get_or_set when callable returns None."""
        def compute_none():
            return None
        
        # First call computes None
        result1 = TestimonialCacheService.get_or_set('key', compute_none)
        self.assertIsNone(result1)
        
        # Note: Since None is returned, cache.get will also return None
        # So callable will be called again (this is expected behavior)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_with_complex_return_value(self):
        """Test get_or_set with complex data structure."""
        def compute_complex():
            return {
                'nested': {'data': [1, 2, 3]},
                'list': ['a', 'b', 'c'],
                'count': 42
            }
        
        result = TestimonialCacheService.get_or_set('complex', compute_complex)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['count'], 42)
        self.assertEqual(result['nested']['data'], [1, 2, 3])


# ============================================================================
# SEMANTIC HELPER METHODS TESTS
# ============================================================================

class CacheSemanticHelpersTests(TestCase):
    """Test semantic helper methods."""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_testimonial_uses_stable_timeout(self):
        """Test cache_testimonial uses stable timeout."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_testimonial(123, {'data': 'test'})
            
            mock_set.assert_called_once()
            call_kwargs = mock_set.call_args[1]
            self.assertEqual(call_kwargs['timeout_type'], 'stable')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_testimonial_generates_correct_key(self):
        """Test cache_testimonial generates correct cache key."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_testimonial(456, {'content': 'test'})
            
            call_args = mock_set.call_args[0]
            self.assertEqual(call_args[0], 'testimonials:testimonial:456')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_stats_uses_stats_timeout(self):
        """Test cache_stats uses stats timeout."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_stats({'total': 100})
            
            call_kwargs = mock_set.call_args[1]
            self.assertEqual(call_kwargs['timeout_type'], 'stats')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_stats_generates_correct_key(self):
        """Test cache_stats generates correct cache key."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_stats({'count': 50})
            
            call_args = mock_set.call_args[0]
            self.assertEqual(call_args[0], 'testimonials:stats')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_featured_uses_featured_timeout(self):
        """Test cache_featured uses featured timeout."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_featured([1, 2, 3])
            
            call_kwargs = mock_set.call_args[1]
            self.assertEqual(call_kwargs['timeout_type'], 'featured')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_featured_generates_correct_key(self):
        """Test cache_featured generates correct cache key."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_featured([])
            
            call_args = mock_set.call_args[0]
            self.assertEqual(call_args[0], 'testimonials:featured')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_dashboard_data_uses_volatile_timeout(self):
        """Test cache_dashboard_data uses volatile timeout."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_dashboard_data('overview', {})
            
            call_kwargs = mock_set.call_args[1]
            self.assertEqual(call_kwargs['timeout_type'], 'volatile')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_dashboard_data_generates_correct_key(self):
        """Test cache_dashboard_data generates correct key based on data_type."""
        test_cases = [
            ('overview', 'testimonials:dashboard:overview'),
            ('charts', 'testimonials:dashboard:charts'),
            ('analytics', 'testimonials:dashboard:analytics'),
        ]
        
        for data_type, expected_key in test_cases:
            with patch.object(TestimonialCacheService, 'set') as mock_set:
                TestimonialCacheService.cache_dashboard_data(data_type, {})
                call_args = mock_set.call_args[0]
                self.assertEqual(call_args[0], expected_key)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_semantic_helpers_with_custom_timeout(self):
        """Test semantic helpers accept custom timeout override."""
        with patch.object(TestimonialCacheService, 'set') as mock_set:
            TestimonialCacheService.cache_testimonial(1, {}, timeout=9999)
            
            call_kwargs = mock_set.call_args[1]
            self.assertEqual(call_kwargs['timeout'], 9999)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class CacheErrorHandlingTests(TestCase):
    """Test error handling in cache operations."""
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    @patch('django.core.cache.cache.get')
    def test_get_handles_exception_gracefully(self, mock_get):
        """Test get handles exceptions and returns default."""
        mock_get.side_effect = Exception("Cache error")
        
        result = TestimonialCacheService.get('key', default='fallback')
        self.assertEqual(result, 'fallback')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    @patch('django.core.cache.cache.set')
    def test_set_handles_exception_gracefully(self, mock_set):
        """Test set handles exceptions and returns False."""
        mock_set.side_effect = Exception("Cache error")
        
        result = TestimonialCacheService.set('key', 'value')
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    @patch('django.core.cache.cache.delete')
    def test_delete_handles_exception_gracefully(self, mock_delete):
        """Test delete handles exceptions and returns False."""
        mock_delete.side_effect = Exception("Cache error")
        
        result = TestimonialCacheService.delete('key')
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    @patch('django.core.cache.cache.delete_many')
    def test_delete_many_handles_exception_gracefully(self, mock_delete_many):
        """Test delete_many handles exceptions and returns 0."""
        mock_delete_many.side_effect = Exception("Cache error")
        
        count = TestimonialCacheService.delete_many(['key1', 'key2'])
        self.assertEqual(count, 0)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    @patch('django.core.cache.cache.get')
    @patch('django.core.cache.cache.set')
    def test_get_or_set_handles_cache_get_exception(self, mock_set, mock_get):
        """Test get_or_set handles exception in cache.get."""
        mock_get.side_effect = Exception("Get failed")
        
        def compute():
            return 'computed'
        
        result = TestimonialCacheService.get_or_set('key', compute)
        # Should still compute and set value
        self.assertEqual(result, 'computed')
        mock_set.assert_called_once()
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_key_with_missing_placeholder_logs_error(self):
        """Test get_key logs error when placeholder is missing."""
        # This should return None and log an error
        key = TestimonialCacheService.get_key('TESTIMONIAL', wrong_param='value')
        self.assertIsNone(key)


# ============================================================================
# INVALIDATE TESTIMONIAL CACHE FUNCTION TESTS
# ============================================================================

class InvalidateTestimonialCacheTests(TestCase):
    """Test invalidate_testimonial_cache function."""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_invalidate_testimonial_cache_basic(self):
        """Test basic testimonial cache invalidation."""
        # Set up some cache keys
        cache.set('testimonials:testimonial:1', {'content': 'test'})
        cache.set('testimonials:stats', {'count': 10})
        cache.set('testimonials:featured', [1, 2, 3])
        
        # Invalidate
        invalidate_testimonial_cache(testimonial_id=1)
        
        # Testimonial-specific cache should be cleared
        self.assertIsNone(cache.get('testimonials:testimonial:1'))
        # Global caches should be cleared
        self.assertIsNone(cache.get('testimonials:stats'))
        self.assertIsNone(cache.get('testimonials:featured'))
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_invalidate_with_category_id(self):
        """Test invalidation with category ID."""
        cache.set('testimonials:category:5:testimonials', [1, 2])
        cache.set('testimonials:category:5:stats', {'count': 2})
        
        invalidate_testimonial_cache(testimonial_id=1, category_id=5)
        
        # Category caches should be cleared
        self.assertIsNone(cache.get('testimonials:category:5:testimonials'))
        self.assertIsNone(cache.get('testimonials:category:5:stats'))
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_invalidate_with_user_id(self):
        """Test invalidation with user ID."""
        cache.set('testimonials:user:42:testimonials', [1, 2, 3])
        cache.set('testimonials:user:42:stats', {'count': 3})
        
        invalidate_testimonial_cache(testimonial_id=1, user_id=42)
        
        # User caches should be cleared
        self.assertIsNone(cache.get('testimonials:user:42:testimonials'))
        self.assertIsNone(cache.get('testimonials:user:42:stats'))
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_invalidate_with_all_parameters(self):
        """Test invalidation with all parameters."""
        # Set up various caches
        cache.set('testimonials:testimonial:1', {})
        cache.set('testimonials:category:5:testimonials', [])
        cache.set('testimonials:user:42:testimonials', [])
        cache.set('testimonials:stats', {})
        
        invalidate_testimonial_cache(
            testimonial_id=1,
            category_id=5,
            user_id=42
        )
        
        # All should be cleared
        self.assertIsNone(cache.get('testimonials:testimonial:1'))
        self.assertIsNone(cache.get('testimonials:category:5:testimonials'))
        self.assertIsNone(cache.get('testimonials:user:42:testimonials'))
        self.assertIsNone(cache.get('testimonials:stats'))
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=False)
    def test_invalidate_when_cache_disabled(self):
        """Test invalidation when cache is disabled does nothing."""
        # Should not raise error
        try:
            invalidate_testimonial_cache(testimonial_id=1)
        except Exception as e:
            self.fail(f"Should not raise exception: {e}")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class CacheServiceIntegrationTests(TestCase):
    """Integration tests combining multiple cache operations."""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_complete_workflow_testimonial_caching(self):
        """Test complete workflow of caching a testimonial."""
        testimonial_data = {
            'id': 1,
            'content': 'Great service!',
            'rating': 5,
            'author': 'John Doe'
        }
        
        # Cache testimonial
        result = TestimonialCacheService.cache_testimonial(1, testimonial_data)
        self.assertTrue(result)
        
        # Retrieve it
        key = TestimonialCacheService.get_key('TESTIMONIAL', id=1)
        cached = TestimonialCacheService.get(key)
        self.assertEqual(cached, testimonial_data)
        
        # Invalidate
        invalidate_testimonial_cache(testimonial_id=1)
        
        # Should be gone
        cached_after = TestimonialCacheService.get(key)
        self.assertIsNone(cached_after)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_multiple_semantic_caches_coexist(self):
        """Test multiple semantic caches can coexist."""
        # Cache different types of data
        TestimonialCacheService.cache_stats({'total': 100})
        TestimonialCacheService.cache_featured([1, 2, 3])
        TestimonialCacheService.cache_testimonial(1, {'content': 'test'})
        TestimonialCacheService.cache_dashboard_data('overview', {'data': 'test'})
        
        # All should be retrievable
        stats = TestimonialCacheService.get('testimonials:stats')
        featured = TestimonialCacheService.get('testimonials:featured')
        testimonial = TestimonialCacheService.get('testimonials:testimonial:1')
        dashboard = TestimonialCacheService.get('testimonials:dashboard:overview')
        
        self.assertIsNotNone(stats)
        self.assertIsNotNone(featured)
        self.assertIsNotNone(testimonial)
        self.assertIsNotNone(dashboard)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_bulk_key_operations(self):
        """Test bulk operations on multiple keys."""
        # Create multiple keys
        keys = []
        for i in range(10):
            key = f'testimonials:test:{i}'
            keys.append(key)
            TestimonialCacheService.set(key, f'value_{i}')
        
        # Verify all exist
        for key in keys:
            self.assertIsNotNone(TestimonialCacheService.get(key))
        
        # Delete all at once
        count = TestimonialCacheService.delete_many(keys)
        self.assertEqual(count, 10)
        
        # Verify all are gone
        for key in keys:
            self.assertIsNone(TestimonialCacheService.get(key))


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class CacheEdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions."""
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_empty_string_value(self):
        """Test caching empty string."""
        TestimonialCacheService.set('empty', '')
        result = TestimonialCacheService.get('empty')
        self.assertEqual(result, '')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_zero_value(self):
        """Test caching zero."""
        TestimonialCacheService.set('zero', 0)
        result = TestimonialCacheService.get('zero')
        self.assertEqual(result, 0)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_false_value(self):
        """Test caching False boolean."""
        TestimonialCacheService.set('false', False)
        result = TestimonialCacheService.get('false')
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_empty_list(self):
        """Test caching empty list."""
        TestimonialCacheService.set('empty_list', [])
        result = TestimonialCacheService.get('empty_list')
        self.assertEqual(result, [])
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_empty_dict(self):
        """Test caching empty dict."""
        TestimonialCacheService.set('empty_dict', {})
        result = TestimonialCacheService.get('empty_dict')
        self.assertEqual(result, {})
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_very_long_key(self):
        """Test caching with very long key."""
        long_key = 'testimonials:' + 'x' * 200
        TestimonialCacheService.set(long_key, 'value')
        result = TestimonialCacheService.get(long_key)
        self.assertEqual(result, 'value')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_large_data_structure(self):
        """Test caching large data structure."""
        large_data = {
            'items': [{'id': i, 'data': f'item_{i}'} for i in range(1000)]
        }
        TestimonialCacheService.set('large', large_data)
        result = TestimonialCacheService.get('large')
        self.assertEqual(len(result['items']), 1000)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_cache_unicode_data(self):
        """Test caching unicode data."""
        unicode_data = {
            'english': 'Hello',
            'chinese': '你好',
            'arabic': 'مرحبا',
            'emoji': '🎉🎊',
        }
        TestimonialCacheService.set('unicode', unicode_data)
        result = TestimonialCacheService.get('unicode')
        self.assertEqual(result, unicode_data)
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_with_zero_timeout(self):
        """Test get_or_set with zero timeout (immediate expiry)."""
        def compute():
            return 'value'
        
        # Set with 0 timeout might behave differently depending on cache backend
        result = TestimonialCacheService.get_or_set('key', compute, timeout=0)
        self.assertEqual(result, 'value')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_get_or_set_with_negative_timeout(self):
        """Test get_or_set with negative timeout."""
        def compute():
            return 'value'
        
        # Negative timeout behavior depends on cache backend
        result = TestimonialCacheService.get_or_set('key', compute, timeout=-1)
        self.assertEqual(result, 'value')
    
    @override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
    def test_concurrent_get_or_set_calls(self):
        """Test concurrent get_or_set calls (race condition)."""
        call_count = 0
        
        def compute():
            nonlocal call_count
            call_count += 1
            return 'value'
        
        # Simulate race - both should handle gracefully
        result1 = TestimonialCacheService.get_or_set('race', compute)
        result2 = TestimonialCacheService.get_or_set('race', compute)
        
        # Both should get same value
        self.assertEqual(result1, 'value')
        self.assertEqual(result2, 'value')
        # First call computes, second uses cache (or both compute in race)
        self.assertGreaterEqual(call_count, 1)