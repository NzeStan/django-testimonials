# testimonials/api/views.py - FIXED

"""
API views with proper settings respect for USE_REDIS_CACHE and USE_CELERY.
"""

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus, TestimonialMediaType
from ..conf import app_settings

# Import services
from ..services import TestimonialCacheService, TaskExecutor
from ..utils import log_testimonial_action

from .serializers import (
    TestimonialSerializer,
    TestimonialAdminDetailSerializer,
    TestimonialUserDetailSerializer,
    TestimonialCreateSerializer,
    TestimonialCategorySerializer,
    TestimonialMediaSerializer,
    TestimonialAdminActionSerializer,
    TestimonialAdminSerializer,
    TestimonialUserSerializer,
)
from .permissions import (
    IsAdminOrReadOnly,
    IsTestimonialAuthorOrReadOnly,
    CanModerateTestimonial
)
from .filters import TestimonialFilter


class OptimizedPagination(PageNumberPagination):
    """
    Optimized pagination for high-performance API responses.
    """
    page_size = app_settings.PAGINATION_SIZE
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """Enhanced pagination response with cache headers."""
        response = super().get_paginated_response(data)
        
        # ✅ FIXED: Only add cache headers if Redis is enabled
        if app_settings.USE_REDIS_CACHE:
            response['Cache-Control'] = f'public, max-age={app_settings.CACHE_TIMEOUT}'
            response['Vary'] = 'Accept, Accept-Language, Authorization'
        
        return response


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    Highly optimized API endpoint for testimonials with proper settings respect.
    """
    queryset = Testimonial.objects.optimized_for_api()
    serializer_class = TestimonialSerializer
    pagination_class = OptimizedPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TestimonialFilter
    search_fields = ['author_name', 'company', 'content', 'title']
    ordering_fields = ['created_at', 'rating', 'display_order', 'approved_at']
    ordering = ['-display_order', '-created_at']
    
    def get_queryset(self):
        """Optimized queryset with comprehensive prefetching and permission filtering."""
        user = self.request.user
        
        # Base queryset with optimized relations
        queryset = Testimonial.objects.optimized_for_api()
        
        # Permission-based filtering
        if self.is_moderator_or_admin(user):
            return queryset
        elif user.is_authenticated:
            return queryset.filter(
                Q(status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]) |
                Q(author=user)
            )
        else:
            return queryset.published()
    
    def get_serializer_class(self):
        """
        🔒 CRITICAL SECURITY FIX:
        Return appropriate serializer based on user role and action.
        Now properly handles DETAIL vs LIST views.
        """
        request = self.request
        user = getattr(request, 'user', None)
        is_admin = user and user.is_authenticated and (user.is_staff or user.is_superuser)
        
        # Creation uses dedicated serializer
        if self.action == 'create':
            return TestimonialCreateSerializer
        
        # Admin actions
        if self.action in ['moderate', 'bulk_action']:
            return TestimonialAdminActionSerializer
        
        # 🔒 DETAIL VIEW (retrieve, update, partial_update)
        if self.action in ['retrieve', 'update', 'partial_update']:
            if is_admin:
                return TestimonialAdminDetailSerializer  # ✅ Shows ip_address, extra_data
            else:
                return TestimonialUserDetailSerializer  # ✅ Shows response_at, but NOT ip/rejection_reason
        
        # 🔒 LIST VIEW (list)
        if is_admin:
            return TestimonialAdminSerializer  # Full fields
        
        return TestimonialUserSerializer  # Limited fields
    
    def get_permissions(self):
        """Dynamic permissions based on action."""
        if self.action in ['create']:
            permission_classes = [permissions.AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsTestimonialAuthorOrReadOnly]
        elif self.action in ['moderate', 'bulk_action']:
            permission_classes = [CanModerateTestimonial]
        else:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def is_moderator_or_admin(self, user):
        """Check if user is moderator or admin."""
        return user and user.is_authenticated and (
            user.is_staff or 
            user.is_superuser or 
            user.has_perm('testimonials.moderate_testimonial')
        )
    
    def create(self, request, *args, **kwargs):
        """
        ✅ FIXED: Properly respects USE_CELERY setting.
        TaskExecutor handles the fallback internally.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform creation
        testimonial = self.perform_create(serializer)
        
        # ✅ TaskExecutor automatically checks USE_CELERY internally
        # No need for explicit if statement here
        try:
            from ..tasks import send_admin_notification
            TaskExecutor.execute(
                send_admin_notification,
                str(testimonial.pk),
                'new_testimonial'
            )
        except Exception as e:
            log_testimonial_action(
                testimonial, 
                "notification_failed", 
                request.user, 
                str(e)
            )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Optimized update with cache invalidation."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Store old values for cache invalidation
        old_status = instance.status
        old_category_id = instance.category_id
        
        self.perform_update(serializer)
        
        # ✅ Cache invalidation respects USE_REDIS_CACHE internally
        if (serializer.instance.status != old_status or 
            serializer.instance.category_id != old_category_id):
            TestimonialCacheService.invalidate_testimonial(
                testimonial_id=instance.pk,
                category_id=old_category_id,
                user_id=instance.author_id
            )
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Optimized destroy with comprehensive cleanup."""
        instance = self.get_object()
        testimonial_id = instance.pk
        category_id = instance.category_id
        user_id = instance.author_id
        
        # Log deletion
        log_testimonial_action(instance, "delete", request.user)
        
        # Perform deletion
        self.perform_destroy(instance)
        
        # ✅ Cache invalidation respects USE_REDIS_CACHE internally
        TestimonialCacheService.invalidate_testimonial(
            testimonial_id=testimonial_id,
            category_id=category_id,
            user_id=user_id
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def perform_create(self, serializer):
        """Enhanced creation with user association and logging."""
        testimonial = serializer.save()
        log_testimonial_action(testimonial, "create", self.request.user)
        return testimonial
    
    def perform_update(self, serializer):
        """Enhanced update with logging."""
        testimonial = serializer.save()
        log_testimonial_action(testimonial, "update", self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[CanModerateTestimonial])
    def approve(self, request, pk=None):
        """Approve a testimonial."""
        testimonial = self.get_object()
        testimonial.approve(user=request.user)
        
        # ✅ Cache invalidation respects USE_REDIS_CACHE internally
        TestimonialCacheService.invalidate_testimonial(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )
        
        return Response({
            'status': 'success',
            'message': _('Testimonial approved successfully.')
        })
    
    @action(detail=True, methods=['post'], permission_classes=[CanModerateTestimonial])
    def reject(self, request, pk=None):
        """Reject a testimonial."""
        testimonial = self.get_object()
        reason = request.data.get('reason', '')
        
        testimonial.reject(reason=reason, user=request.user)
        
        # ✅ Cache invalidation respects USE_REDIS_CACHE internally
        TestimonialCacheService.invalidate_testimonial(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )
        
        return Response({
            'status': 'success',
            'message': _('Testimonial rejected successfully.')
        })
    
    @action(detail=True, methods=['post'], permission_classes=[CanModerateTestimonial])
    def feature(self, request, pk=None):
        """Feature a testimonial."""
        testimonial = self.get_object()
        testimonial.feature(user=request.user)
        
        # ✅ Cache invalidation respects USE_REDIS_CACHE internally
        TestimonialCacheService.invalidate_testimonial(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )
        
        return Response({
            'status': 'success',
            'message': _('Testimonial featured successfully.')
        })
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        ✅ FIXED: Explicitly handles USE_REDIS_CACHE setting.
        Get featured testimonials with appropriate caching.
        """
        def get_featured_data():
            queryset = self.get_queryset().featured()[:10]
            serializer = self.get_serializer(queryset, many=True)
            return serializer.data
        
        # ✅ FIXED: Check setting explicitly for clarity
        if app_settings.USE_REDIS_CACHE:
            data = TestimonialCacheService.get_or_set(
                TestimonialCacheService.get_key('FEATURED'),
                get_featured_data,
                timeout_type='featured'
            )
        else:
            data = get_featured_data()
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        ✅ FIXED: Explicitly handles USE_REDIS_CACHE setting.
        Get testimonial statistics with appropriate caching.
        """
        def get_stats_data():
            return Testimonial.objects.get_stats()
        
        # ✅ FIXED: Check setting explicitly for clarity
        if app_settings.USE_REDIS_CACHE:
            stats = TestimonialCacheService.get_or_set(
                TestimonialCacheService.get_key('STATS'),
                get_stats_data,
                timeout_type='stats'
            )
        else:
            stats = get_stats_data()
        
        return Response(stats)
    
    @action(detail=False, methods=['post'], permission_classes=[CanModerateTestimonial])
    def bulk_action(self, request):
        """Perform bulk actions on testimonials."""
        serializer = TestimonialAdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        testimonial_ids = serializer.validated_data['testimonial_ids']
        reason = serializer.validated_data.get('reason', '')
        
        testimonials = Testimonial.objects.filter(id__in=testimonial_ids)
        count = 0
        
        for testimonial in testimonials:
            if action_type == 'approve':
                testimonial.approve(user=request.user)
                count += 1
            elif action_type == 'reject':
                testimonial.reject(reason=reason, user=request.user)
                count += 1
            elif action_type == 'feature':
                testimonial.feature(user=request.user)
                count += 1
            elif action_type == 'archive':
                testimonial.archive(user=request.user)
                count += 1
        
        # ✅ Cache invalidation respects USE_REDIS_CACHE internally
        TestimonialCacheService.invalidate_all()
        
        return Response({
            'status': 'success',
            'count': count,
            'message': _('Successfully performed %(action)s on %(count)d testimonials.') % {
                'action': action_type,
                'count': count
            }
        })
    
    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def remove_avatar(self, request, pk=None):
        """
        🆕 NEW ENDPOINT: Remove avatar from testimonial.
        Users can remove their own avatar, admins can remove any.
        """
        testimonial = self.get_object()
        user = request.user
        
        # 🔒 Security: Users can only remove their own avatar
        if not (user.is_staff or user.is_superuser):
            if testimonial.author != user:
                return Response(
                    {'detail': _('You can only remove your own avatar.')},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Remove the avatar
        if testimonial.avatar:
            # Delete the file
            try:
                testimonial.avatar.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete avatar file: {e}")
            
            # Clear the field
            testimonial.avatar = None
            testimonial.save(update_fields=['avatar', 'updated_at'])
            
            # Invalidate cache
            TestimonialCacheService.invalidate_testimonial(
                testimonial_id=testimonial.pk,
                category_id=testimonial.category_id,
                user_id=testimonial.author_id
            )
            
            log_testimonial_action(testimonial, "remove_avatar", user)
            
            return Response({
                'status': 'success',
                'message': _('Avatar removed successfully.')
            })
        else:
            return Response(
                {'detail': _('No avatar to remove.')},
                status=status.HTTP_400_BAD_REQUEST
            )


class TestimonialCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for testimonial categories."""
    queryset = TestimonialCategory.objects.active()
    serializer_class = TestimonialCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = OptimizedPagination
    
    def get_queryset(self):
        """Optimized queryset with testimonial counts."""
        return TestimonialCategory.objects.with_testimonial_counts()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        ✅ FIXED: Explicitly handles USE_REDIS_CACHE setting.
        Get category statistics with appropriate caching.
        """
        def get_category_stats_data():
            return TestimonialCategory.objects.get_stats()
        
        # ✅ FIXED: Check setting explicitly
        if app_settings.USE_REDIS_CACHE:
            stats = TestimonialCacheService.get_or_set(
                TestimonialCacheService.get_key('CATEGORY_STATS', id='all'),
                get_category_stats_data,
                timeout_type='stats'
            )
        else:
            stats = get_category_stats_data()
        
        return Response(stats)


class TestimonialMediaViewSet(viewsets.ModelViewSet):
    """API endpoint for testimonial media."""
    queryset = TestimonialMedia.objects.all()
    serializer_class = TestimonialMediaSerializer
    permission_classes = [IsTestimonialAuthorOrReadOnly]
    pagination_class = OptimizedPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['testimonial', 'media_type', 'is_primary']
    ordering_fields = ['order', 'created_at']
    ordering = ['-is_primary', 'order', '-created_at']
    
    def get_queryset(self):
        """Optimized queryset with permission filtering."""
        user = self.request.user
        queryset = TestimonialMedia.objects.optimized_for_api()
        
        # Filter based on testimonial permissions
        if not user.is_staff:
            queryset = queryset.filter(
                testimonial__status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """
        ✅ FIXED: Properly respects USE_CELERY setting.
        Create media with async processing.
        """
        media = serializer.save()
        
        # ✅ TaskExecutor automatically checks USE_CELERY internally
        try:
            from ..tasks import process_media
            TaskExecutor.execute(process_media, str(media.pk))
        except Exception as e:
            log_testimonial_action(
                media.testimonial, 
                "media_processing_failed", 
                self.request.user, 
                str(e)
            )