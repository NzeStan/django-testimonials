# testimonials/tests/test_permissions.py

"""
Comprehensive tests for API permissions.
Tests cover all permission classes, view-level and object-level permissions,
and various user scenarios (anonymous, authenticated, staff, admin, moderator).
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIRequestFactory
from unittest.mock import Mock

from testimonials.models import Testimonial, TestimonialMedia, TestimonialCategory
from testimonials.constants import TestimonialStatus, TestimonialMediaType
from testimonials.api.permissions import (
    IsAdminOrReadOnly,
    IsTestimonialAuthorOrReadOnly,
    CanModerateTestimonial
)

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class PermissionTestCase(TestCase):
    """Base test case for permission tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all permission tests."""
        # Create users with different roles
        cls.anonymous_user = Mock()
        cls.anonymous_user.is_authenticated = False
        cls.anonymous_user.is_staff = False
        cls.anonymous_user.is_superuser = False
        
        cls.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='pass123'
        )
        
        cls.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123'
        )
        
        cls.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='pass123',
            is_staff=True
        )
        
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='pass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create moderator user with moderation group
        cls.moderator_user = User.objects.create_user(
            username='moderator',
            email='moderator@example.com',
            password='pass123'
        )
        cls.moderator_group = Group.objects.create(name='Content Manager')
        cls.moderator_user.groups.add(cls.moderator_group)
        
        # Create test objects
        cls.category = TestimonialCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        cls.testimonial = Testimonial.objects.create(
            author=cls.regular_user,
            author_name='Regular User',
            content='Test testimonial content',
            rating=5,
            category=cls.category
        )
        
        cls.media = TestimonialMedia.objects.create(
            testimonial=cls.testimonial,
            media_type=TestimonialMediaType.IMAGE,
            title='Test media'
        )
    
    def setUp(self):
        """Set up for each test."""
        self.factory = APIRequestFactory()


# ============================================================================
# IsAdminOrReadOnly PERMISSION TESTS
# ============================================================================

class IsAdminOrReadOnlyTests(PermissionTestCase):
    """Tests for IsAdminOrReadOnly permission."""
    
    def setUp(self):
        super().setUp()
        self.permission = IsAdminOrReadOnly()
        self.view = Mock()
    
    # === View-level permissions (has_permission) ===
    
    def test_anonymous_user_can_read(self):
        """Test anonymous user can perform safe methods."""
        request = self.factory.get('/api/testimonials/')
        request.user = self.anonymous_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_anonymous_user_cannot_write(self):
        """Test anonymous user cannot perform unsafe methods."""
        request = self.factory.post('/api/testimonials/')
        request.user = self.anonymous_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_regular_user_can_read(self):
        """Test regular user can perform safe methods."""
        request = self.factory.get('/api/testimonials/')
        request.user = self.regular_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_regular_user_cannot_write(self):
        """Test regular user cannot perform unsafe methods."""
        request = self.factory.post('/api/testimonials/')
        request.user = self.regular_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_staff_user_can_read(self):
        """Test staff user can perform safe methods."""
        request = self.factory.get('/api/testimonials/')
        request.user = self.staff_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_staff_user_can_write(self):
        """Test staff user can perform unsafe methods."""
        request = self.factory.post('/api/testimonials/')
        request.user = self.staff_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_admin_user_can_read(self):
        """Test admin user can perform safe methods."""
        request = self.factory.get('/api/testimonials/')
        request.user = self.admin_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_admin_user_can_write(self):
        """Test admin user can perform unsafe methods."""
        request = self.factory.post('/api/testimonials/')
        request.user = self.admin_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_put_method_requires_admin(self):
        """Test PUT requires admin."""
        request = self.factory.put('/api/testimonials/1/')
        request.user = self.regular_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_patch_method_requires_admin(self):
        """Test PATCH requires admin."""
        request = self.factory.patch('/api/testimonials/1/')
        request.user = self.regular_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_delete_method_requires_admin(self):
        """Test DELETE requires admin."""
        request = self.factory.delete('/api/testimonials/1/')
        request.user = self.regular_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_options_method_allowed(self):
        """Test OPTIONS is a safe method."""
        request = self.factory.options('/api/testimonials/')
        request.user = self.anonymous_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_head_method_allowed(self):
        """Test HEAD is a safe method."""
        request = self.factory.head('/api/testimonials/')
        request.user = self.anonymous_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )


# ============================================================================
# IsTestimonialAuthorOrReadOnly PERMISSION TESTS
# ============================================================================

class IsTestimonialAuthorOrReadOnlyTests(PermissionTestCase):
    """Tests for IsTestimonialAuthorOrReadOnly permission."""
    
    def setUp(self):
        super().setUp()
        self.permission = IsTestimonialAuthorOrReadOnly()
        self.view = Mock()
    
    # === View-level permissions ===
    
    def test_view_permission_safe_methods_anonymous(self):
        """Test view-level permission for safe methods (anonymous)."""
        request = self.factory.get('/api/testimonials/')
        request.user = self.anonymous_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_view_permission_unsafe_methods_anonymous(self):
        """Test view-level permission for unsafe methods (anonymous)."""
        request = self.factory.post('/api/testimonials/')
        request.user = self.anonymous_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_view_permission_unsafe_methods_authenticated(self):
        """Test view-level permission for unsafe methods (authenticated)."""
        request = self.factory.post('/api/testimonials/')
        request.user = self.regular_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    # === Object-level permissions for Testimonial ===
    
    def test_object_permission_safe_methods(self):
        """Test object permission for safe methods."""
        request = self.factory.get('/api/testimonials/1/')
        request.user = self.anonymous_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_author_can_edit(self):
        """Test author can edit their own testimonial."""
        request = self.factory.put('/api/testimonials/1/')
        request.user = self.regular_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_other_user_cannot_edit(self):
        """Test other user cannot edit testimonial."""
        request = self.factory.put('/api/testimonials/1/')
        request.user = self.other_user
        
        self.assertFalse(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_staff_can_edit_any(self):
        """Test staff can edit any testimonial."""
        request = self.factory.put('/api/testimonials/1/')
        request.user = self.staff_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_admin_can_edit_any(self):
        """Test admin can edit any testimonial."""
        request = self.factory.put('/api/testimonials/1/')
        request.user = self.admin_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_author_can_delete(self):
        """Test author can delete their own testimonial."""
        request = self.factory.delete('/api/testimonials/1/')
        request.user = self.regular_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_other_user_cannot_delete(self):
        """Test other user cannot delete testimonial."""
        request = self.factory.delete('/api/testimonials/1/')
        request.user = self.other_user
        
        self.assertFalse(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    # === Object-level permissions for TestimonialMedia ===
    
    def test_media_permission_author_can_edit(self):
        """Test author can edit media on their testimonial."""
        request = self.factory.put('/api/media/1/')
        request.user = self.regular_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.media
            )
        )
    
    def test_media_permission_other_user_cannot_edit(self):
        """Test other user cannot edit media on testimonial."""
        request = self.factory.put('/api/media/1/')
        request.user = self.other_user
        
        self.assertFalse(
            self.permission.has_object_permission(
                request, self.view, self.media
            )
        )
    
    def test_media_permission_staff_can_edit_any(self):
        """Test staff can edit any media."""
        request = self.factory.put('/api/media/1/')
        request.user = self.staff_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.media
            )
        )
    
    def test_media_permission_admin_can_edit_any(self):
        """Test admin can edit any media."""
        request = self.factory.put('/api/media/1/')
        request.user = self.admin_user
        
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.media
            )
        )


# ============================================================================
# CanModerateTestimonial PERMISSION TESTS
# ============================================================================

class CanModerateTestimonialTests(PermissionTestCase):
    """Tests for CanModerateTestimonial permission."""
    
    def setUp(self):
        super().setUp()
        self.permission = CanModerateTestimonial()
        self.view = Mock()
    
    # === View-level permissions ===
    
    def test_anonymous_cannot_moderate(self):
        """Test anonymous user cannot moderate."""
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.anonymous_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_regular_user_cannot_moderate(self):
        """Test regular user cannot moderate."""
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.regular_user
        
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_staff_can_moderate(self):
        """Test staff user can moderate."""
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.staff_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_admin_can_moderate(self):
        """Test admin user can moderate."""
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.admin_user
        
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )
    
    def test_moderator_can_moderate(self):
        """Test user in moderation group can moderate."""
        from django.conf import settings
        
        # Temporarily set moderation roles
        with self.settings(TESTIMONIALS_MODERATION_ROLES=['Content Manager']):
            request = self.factory.post('/api/testimonials/1/approve/')
            request.user = self.moderator_user
            
            self.assertTrue(
                self.permission.has_permission(request, self.view)
            )
    
    def test_moderator_without_setting_cannot_moderate(self):
        """Test moderator cannot moderate if not in configured roles."""
        # MODERATION_ROLES is empty by default
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.moderator_user
        
        # Should fail because MODERATION_ROLES doesn't include 'Content Manager'
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )
    
    def test_user_in_wrong_group_cannot_moderate(self):
        """Test user in different group cannot moderate."""
        other_group = Group.objects.create(name='Other Group')
        user_with_other_group = User.objects.create_user(
            username='other_group_user',
            email='other@example.com'
        )
        user_with_other_group.groups.add(other_group)
        
        with self.settings(TESTIMONIALS_MODERATION_ROLES=['Content Manager']):
            request = self.factory.post('/api/testimonials/1/approve/')
            request.user = user_with_other_group
            
            self.assertFalse(
                self.permission.has_permission(request, self.view)
            )
    
    # === Object-level permissions ===
    
    def test_object_permission_delegates_to_view_permission(self):
        """Test object permission delegates to view permission."""
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.admin_user
        
        # Should use has_permission logic
        self.assertTrue(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )
    
    def test_object_permission_regular_user_denied(self):
        """Test object permission denies regular user."""
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.regular_user
        
        self.assertFalse(
            self.permission.has_object_permission(
                request, self.view, self.testimonial
            )
        )


# ============================================================================
# EDGE CASE AND SECURITY TESTS
# ============================================================================

class PermissionEdgeCaseTests(PermissionTestCase):
    """Tests for edge cases and security scenarios."""
    
    def test_none_user(self):
        """Test permission with None user."""
        permission = IsAdminOrReadOnly()
        view = Mock()
        
        request = self.factory.post('/api/testimonials/')
        request.user = None
        
        # Should handle gracefully
        result = permission.has_permission(request, view)
        self.assertFalse(result)
    
    def test_user_without_groups_attribute(self):
        """Test moderator permission with user missing groups."""
        permission = CanModerateTestimonial()
        view = Mock()
        
        # Create mock user without groups
        user = Mock()
        user.is_authenticated = True
        user.is_staff = False
        user.is_superuser = False
        # Don't set groups attribute
        
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = user
        
        # Should handle gracefully
        result = permission.has_permission(request, view)
        self.assertFalse(result)
    
    def test_deleted_testimonial_author(self):
        """Test permission when testimonial author is deleted."""
        permission = IsTestimonialAuthorOrReadOnly()
        view = Mock()
        
        # Create testimonial with author
        testimonial = Testimonial.objects.create(
            author=self.other_user,
            content='Test content',
            rating=5
        )
        
        # Try to edit as different user
        request = self.factory.put(f'/api/testimonials/{testimonial.pk}/')
        request.user = self.regular_user
        
        result = permission.has_object_permission(request, view, testimonial)
        self.assertFalse(result)
    
    def test_testimonial_without_author(self):
        """Test permission on testimonial with no author (anonymous)."""
        permission = IsTestimonialAuthorOrReadOnly()
        view = Mock()
        
        # Create anonymous testimonial
        testimonial = Testimonial.objects.create(
            author_name='Anonymous User',
            content='Anonymous testimonial',
            rating=5,
            is_anonymous=True
        )
        
        # Try to edit as regular user
        request = self.factory.put(f'/api/testimonials/{testimonial.pk}/')
        request.user = self.regular_user
        
        # Should deny since user is not the author
        result = permission.has_object_permission(request, view, testimonial)
        self.assertFalse(result)
    
    def test_staff_flag_without_superuser(self):
        """Test that staff without superuser can still moderate."""
        permission = CanModerateTestimonial()
        view = Mock()
        
        # Staff but not superuser
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = self.staff_user
        
        self.assertTrue(
            permission.has_permission(request, view)
        )
    
    def test_superuser_without_staff(self):
        """Test superuser without staff flag can moderate."""
        permission = CanModerateTestimonial()
        view = Mock()
        
        # Create superuser without staff flag
        superuser = User.objects.create_user(
            username='superuser_no_staff',
            email='super@example.com',
            is_superuser=True,
            is_staff=False
        )
        
        request = self.factory.post('/api/testimonials/1/approve/')
        request.user = superuser
        
        self.assertTrue(
            permission.has_permission(request, view)
        )
    
    def test_multiple_groups_one_matches(self):
        """Test user in multiple groups, one is moderator group."""
        permission = CanModerateTestimonial()
        view = Mock()
        
        # Create user with multiple groups
        group1 = Group.objects.create(name='Group 1')
        group2 = Group.objects.create(name='Moderators')
        
        user = User.objects.create_user(
            username='multi_group',
            email='multi@example.com'
        )
        user.groups.add(group1, group2)
        
        with self.settings(TESTIMONIALS_MODERATION_ROLES=['Moderators']):
            request = self.factory.post('/api/testimonials/1/approve/')
            request.user = user
            
            self.assertTrue(
                permission.has_permission(request, view)
            )
    
    def test_case_sensitivity_in_group_names(self):
        """Test that group name matching is case-sensitive."""
        permission = CanModerateTestimonial()
        view = Mock()
        
        # Create group with lowercase name
        group = Group.objects.create(name='moderators')
        user = User.objects.create_user(
            username='lowercase_group',
            email='lower@example.com'
        )
        user.groups.add(group)
        
        # Config has uppercase
        with self.settings(TESTIMONIALS_MODERATION_ROLES=['Moderators']):
            request = self.factory.post('/api/testimonials/1/approve/')
            request.user = user
            
            # Should fail due to case mismatch
            self.assertFalse(
                permission.has_permission(request, view)
            )
    
    def test_empty_moderation_roles_setting(self):
        """Test behavior with empty MODERATION_ROLES."""
        permission = CanModerateTestimonial()
        view = Mock()
        
        with self.settings(TESTIMONIALS_MODERATION_ROLES=[]):
            request = self.factory.post('/api/testimonials/1/approve/')
            request.user = self.moderator_user
            
            # Should deny since no roles configured
            self.assertFalse(
                permission.has_permission(request, view)
            )
    
    def test_permission_on_different_object_types(self):
        """Test IsTestimonialAuthorOrReadOnly with various object types."""
        permission = IsTestimonialAuthorOrReadOnly()
        view = Mock()
        
        request = self.factory.put('/api/media/1/')
        request.user = self.regular_user
        
        # Test with media (has testimonial attribute)
        result_media = permission.has_object_permission(request, view, self.media)
        self.assertTrue(result_media)
        
        # Test with testimonial (no testimonial attribute)
        result_testimonial = permission.has_object_permission(
            request, view, self.testimonial
        )
        self.assertTrue(result_testimonial)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class PermissionIntegrationTests(PermissionTestCase):
    """Integration tests for permission combinations."""
    
    def test_admin_or_readonly_and_author_readonly_together(self):
        """Test combining IsAdminOrReadOnly and IsTestimonialAuthorOrReadOnly."""
        admin_permission = IsAdminOrReadOnly()
        author_permission = IsTestimonialAuthorOrReadOnly()
        view = Mock()
        
        # Regular user trying to edit their own testimonial
        request = self.factory.put('/api/testimonials/1/')
        request.user = self.regular_user
        
        # Admin permission would deny (not admin)
        self.assertFalse(admin_permission.has_permission(request, view))
        
        # Author permission would allow (is author)
        self.assertTrue(author_permission.has_permission(request, view))
        self.assertTrue(
            author_permission.has_object_permission(request, view, self.testimonial)
        )
    
    def test_all_permissions_deny_anonymous_write(self):
        """Test that all permissions deny anonymous write operations."""
        permissions = [
            IsAdminOrReadOnly(),
            IsTestimonialAuthorOrReadOnly(),
            CanModerateTestimonial()
        ]
        view = Mock()
        
        request = self.factory.post('/api/testimonials/')
        request.user = self.anonymous_user
        
        for permission in permissions:
            self.assertFalse(
                permission.has_permission(request, view),
                f"{permission.__class__.__name__} should deny anonymous write"
            )
    
    def test_all_permissions_allow_read(self):
        """Test that read-only permissions allow reads for all users."""
        permissions = [
            IsAdminOrReadOnly(),
            IsTestimonialAuthorOrReadOnly(),
        ]
        view = Mock()
        
        users = [
            self.anonymous_user,
            self.regular_user,
            self.staff_user,
            self.admin_user
        ]
        
        for user in users:
            request = self.factory.get('/api/testimonials/')
            request.user = user
            
            for permission in permissions:
                self.assertTrue(
                    permission.has_permission(request, view),
                    f"{permission.__class__.__name__} should allow read for {user}"
                )
    
    def test_permission_escalation_prevention(self):
        """Test that permissions prevent escalation attacks."""
        permission = IsTestimonialAuthorOrReadOnly()
        view = Mock()
        
        # User tries to modify someone else's testimonial
        other_testimonial = Testimonial.objects.create(
            author=self.other_user,
            content='Other user testimonial',
            rating=5
        )
        
        request = self.factory.put(f'/api/testimonials/{other_testimonial.pk}/')
        request.user = self.regular_user
        
        # Should be denied at object level
        self.assertFalse(
            permission.has_object_permission(request, view, other_testimonial)
        )