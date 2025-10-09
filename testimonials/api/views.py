# testimonials/api/views.py - REFACTORED

"""
Refactored API views using services for cache and task management.
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

# Import services instead of utils
from ..services import TestimonialCacheService, TaskExecutor
from ..utils import log_testimonial_action

from .serializers import (
    TestimonialSerializer,
    TestimonialDetailSerializer,
    TestimonialCreateSerializer,
    TestimonialCategorySerializer,
    TestimonialMediaSerializer,
    TestimonialAdminActionSerializer
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
        
        # Add cache headers for better client-side caching
        if app_settings.USE_REDIS_CACHE:
            response['Cache-Control'] = f'public, max-age={app_settings.CACHE_TIMEOUT}'
            response['Vary'] = 'Accept, Accept-Language, Authorization'
        
        return response


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    Highly optimized API endpoint for testimonials with caching and performance monitoring.
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
        """
        Optimized queryset with comprehensive prefetching and permission filtering.
        """
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
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return TestimonialCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return TestimonialDetailSerializer
        elif self.action in ['moderate', 'bulk_action']:
            return TestimonialAdminActionSerializer
        return TestimonialSerializer
    
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
        Optimized creation with background processing.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform creation
        testimonial = self.perform_create(serializer)
        
        # Background processing using TaskExecutor
        if app_settings.USE_CELERY:
            try:
                from ..tasks import send_admin_notification
                TaskExecutor.execute(
                    send_admin_notification,
                    str(testimonial.pk),
                    'new_testimonial'
                )
            except Exception as e:
                log_testimonial_action(testimonial, "async_notification_failed", 
                                    request.user, str(e))
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """
        Optimized update with cache invalidation.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Store old values for cache invalidation
        old_status = instance.status
        old_category_id = instance.category_id
        
        self.perform_update(serializer)
        
        # Invalidate cache if important fields changed using CacheService
        if (serializer.instance.status != old_status or 
            serializer.instance.category_id != old_category_id):
            TestimonialCacheService.invalidate_testimonial(
                testimonial_id=instance.pk,
                category_id=old_category_id,
                user_id=instance.author_id
            )
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Optimized destroy with comprehensive cleanup.
        """
        instance = self.get_object()
        testimonial_id = instance.pk
        category_id = instance.category_id
        user_id = instance.author_id
        
        # Log deletion
        log_testimonial_action(instance, "delete", request.user)
        
        # Perform deletion
        self.perform_destroy(instance)
        
        # Invalidate cache using CacheService
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
        
        # Invalidate cache using CacheService
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
        
        # Invalidate cache using CacheService
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
        
        # Invalidate cache using CacheService
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
    def stats(self, request):
        """Get testimonial statistics with caching."""
        def get_stats_data():
            return Testimonial.objects.get_stats()
        
        # Use CacheService for stats
        stats = TestimonialCacheService.get_or_set(
            TestimonialCacheService.get_key('STATS'),
            get_stats_data,
            timeout=app_settings.CACHE_TIMEOUT
        )
        
        return Response(stats)


class TestimonialCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for testimonial categories.
    """
    queryset = TestimonialCategory.objects.active()
    serializer_class = TestimonialCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = OptimizedPagination
    
    def get_queryset(self):
        """Optimized queryset with testimonial counts."""
        return TestimonialCategory.objects.with_testimonial_counts()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get category statistics with caching."""
        def get_category_stats_data():
            return TestimonialCategory.objects.get_stats()
        
        # Use CacheService
        stats = TestimonialCacheService.get_or_set(
            TestimonialCacheService.get_key('STATS'),
            get_category_stats_data,
            timeout=app_settings.CACHE_TIMEOUT
        )
        
        return Response(stats)


class TestimonialMediaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for testimonial media.
    """
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
        """Create media with async processing."""
        media = serializer.save()
        
        # Process media asynchronously using TaskExecutor
        if app_settings.USE_CELERY:
            try:
                from ..tasks import process_media
                TaskExecutor.execute(process_media, str(media.pk))
            except Exception as e:
                log_testimonial_action(media.testimonial, "media_processing_failed", 
                                    self.request.user, str(e))