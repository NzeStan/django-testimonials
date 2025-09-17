from rest_framework import permissions
from ..conf import app_settings


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow administrators to edit objects.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to admin users
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        )


class IsTestimonialAuthorOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow the author of a testimonial or administrators to edit it.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions require authentication
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admin users can do anything
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if this is a TestimonialMedia object or a Testimonial
        if hasattr(obj, 'testimonial'):
            # This is a TestimonialMedia object
            # Check if the user is the author of the testimonial
            return obj.testimonial.author == request.user
        else:
            # This is a Testimonial object
            # Check if the user is the author
            return obj.author == request.user


class CanModerateTestimonial(permissions.BasePermission):
    """
    Permission to only allow users who can moderate testimonials.
    
    Admins, staff, and users in the specified moderation roles can moderate.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins and staff can always moderate
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is in a moderation role
        if hasattr(request.user, 'groups') and app_settings.MODERATION_ROLES:
            return request.user.groups.filter(
                name__in=app_settings.MODERATION_ROLES
            ).exists()
        
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)