from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.throttling import ScopedRateThrottle

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus
from ..conf import app_settings
from ..utils import (
    log_testimonial_action, 
    invalidate_testimonial_cache, 
    get_cache_key, 
    cache_get_or_set,
    execute_task
)
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
        """Enhanced pagination response with performance metrics."""
        response = super().get_paginated_response(data)
        
        # Add cache headers for better client-side caching
        if app_settings.USE_REDIS_CACHE:
            response['Cache-Control'] = f'public, max-age={app_settings.CACHE_TIMEOUT}'
            response['Vary'] = 'Accept, Accept-Language, Authorization'
        
        return response


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    Highly optimized API endpoint for testimonials with caching, prefetching, and performance monitoring.
    
    list:
        Return a list of published testimonials with optimized queries.
    
    create:
        Create a new testimonial with background processing.
    
    retrieve:
        Return a specific testimonial with all related data preloaded.
    
    update:
        Update a testimonial with cache invalidation.
    
    partial_update:
        Partially update a testimonial with optimized field updates.
    
    destroy:
        Delete a testimonial with comprehensive cleanup.
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
        
        # Permission-based filtering with database optimization
        if self.is_moderator_or_admin(user):
            # Admins and moderators see everything
            return queryset
        elif user.is_authenticated:
            # Authenticated users see published testimonials and their own
            return queryset.filter(
                Q(status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]) |
                Q(author=user)
            )
        else:
            # Anonymous users see only published testimonials
            return queryset.published()
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on action and user permissions.
        """
        if self.action == 'create':
            return TestimonialCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return TestimonialDetailSerializer
        elif self.action in ['moderate', 'bulk_action']:
            return TestimonialAdminActionSerializer
        return TestimonialSerializer
    
    def get_permissions(self):
        """
        Dynamic permissions based on action.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsTestimonialAuthorOrReadOnly()]
        elif self.action in ['moderate', 'approve', 'reject', 'feature', 'archive', 'bulk_action']:
            return [CanModerateTestimonial()]
        elif self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticatedOrReadOnly()]
    
    def get_throttles(self):
        if getattr(self, 'action', None) == 'create':
            self.throttle_scope = 'testimonials_create'
            return [ScopedRateThrottle()]
        return super().get_throttles()
    
    @method_decorator(cache_page(app_settings.CACHE_TIMEOUT))
    def list(self, request, *args, **kwargs):
        """
        Cached list view for better performance.
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Optimized retrieve with caching for individual testimonials.
        """
        instance = self.get_object()
        
        def get_testimonial_data():
            serializer = self.get_serializer(instance)
            return serializer.data
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('testimonial_detail', instance.pk, request.user.id)
            data = cache_get_or_set(cache_key, get_testimonial_data, 
                                  timeout=app_settings.CACHE_TIMEOUT // 2)
        else:
            data = get_testimonial_data()
        
        return Response(data)
    
    def create(self, request, *args, **kwargs):
        """
        Create media with background processing.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # FIXED: Save returns the media instance
        media = serializer.save()
        
        # Background processing
        if app_settings.USE_CELERY:
            try:
                from ..tasks import process_media
                from ..utils import execute_task
                execute_task(process_media, str(media.pk))
            except Exception as e:
                from ..utils import log_testimonial_action
                log_testimonial_action(media.testimonial, "media_processing_failed", 
                                    request.user, str(e))
        
        # Invalidate cache
        invalidate_testimonial_cache(testimonial_id=media.testimonial_id)
        
        headers = self.get_success_headers(serializer.data)
        
        # FIXED: Return the single created media, not a list
        # The response should be a single object with 201 status
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """
        Optimized update with cache invalidation.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Store old values for comparison
        old_status = instance.status
        old_category_id = instance.category_id
        
        self.perform_update(serializer)
        
        # Invalidate cache if important fields changed
        if (serializer.instance.status != old_status or 
            serializer.instance.category_id != old_category_id):
            invalidate_testimonial_cache(
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
        
        # Invalidate cache
        invalidate_testimonial_cache(
            testimonial_id=testimonial_id,
            category_id=category_id,
            user_id=user_id
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def perform_create(self, serializer):
        """
        Enhanced creation with user association and logging.
        """
        user = self.request.user
        if user.is_authenticated:
            testimonial = serializer.save(author=user)
        else:
            testimonial = serializer.save()
        
        # Log creation
        log_testimonial_action(testimonial, "create", user)
        
        return testimonial
    
    def is_moderator_or_admin(self, user):
        """
        Optimized moderator check with caching.
        """
        if not user or not user.is_authenticated:
            return False
        
        # Cache user permissions for the session
        cache_key = f"user_permissions:{user.id}"
        
        def check_permissions():
            return (
                user.is_staff or 
                user.is_superuser or 
                (hasattr(user, 'groups') and 
                 user.groups.filter(name__in=app_settings.MODERATION_ROLES).exists())
            )
        
        if app_settings.USE_REDIS_CACHE:
            return cache_get_or_set(cache_key, check_permissions, timeout=300)  # 5 min cache
        
        return check_permissions()
    
    @action(detail=False, methods=['get'])
    def mine(self, request):
        """
        Optimized user testimonials with caching.
        """
        if not request.user.is_authenticated:
            return Response(
                {"detail": _("Authentication required to view your testimonials.")},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        def get_user_testimonials():
            testimonials = self.get_queryset().filter(author=request.user)
            page = self.paginate_queryset(testimonials)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(testimonials, many=True)
            return Response(serializer.data)
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('user_testimonials', request.user.id)
            return cache_get_or_set(cache_key, get_user_testimonials, 
                                  timeout=app_settings.CACHE_TIMEOUT // 4)
        
        return get_user_testimonials()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Optimized pending testimonials for moderators.
        """
        if not self.is_moderator_or_admin(request.user):
            return Response(
                {"detail": _("You do not have permission to view pending testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        testimonials = self.get_queryset().pending()
        page = self.paginate_queryset(testimonials)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(testimonials, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Cached featured testimonials endpoint.
        """
        def get_featured_testimonials():
            testimonials = self.get_queryset().featured()
            page = self.paginate_queryset(testimonials)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(testimonials, many=True)
            return Response(serializer.data)
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('featured_testimonials_api')
            return cache_get_or_set(cache_key, get_featured_testimonials)
        
        return get_featured_testimonials()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Cached testimonial statistics endpoint.
        """
        def get_stats():
            return Response(Testimonial.objects.get_stats())
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('testimonial_stats')
            return cache_get_or_set(cache_key, get_stats, 
                                  timeout=app_settings.CACHE_TIMEOUT * 2)
        
        return get_stats()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Optimized testimonial approval with background processing.
        """
        if not self.is_moderator_or_admin(request.user):
            return Response(
                {"detail": _("You do not have permission to approve testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )

        testimonial = self.get_object()

        if testimonial.status == TestimonialStatus.APPROVED:
            return Response(
                {"detail": _("Testimonial is already approved.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Approve the testimonial
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.approved_at = timezone.now()
        testimonial.approved_by = request.user
        testimonial.save(update_fields=['status', 'approved_at', 'approved_by'])

        # Background email notification
        if app_settings.USE_CELERY and testimonial.author_email:
            try:
                from ..tasks import send_testimonial_email
                execute_task(
                    send_testimonial_email,
                    str(testimonial.pk),
                    'approved',
                    testimonial.author_email
                )
            except Exception as e:
                log_testimonial_action(testimonial, "approval_email_failed", 
                                     request.user, str(e))

        # Log the approval
        log_testimonial_action(testimonial, "approve", request.user)

        # Invalidate cache
        invalidate_testimonial_cache(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Optimized testimonial rejection with validation.
        """
        if not self.is_moderator_or_admin(request.user):
            return Response(
                {"detail": _("You do not have permission to reject testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )

        testimonial = self.get_object()
        rejection_reason = request.data.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            return Response(
                {"detail": _("Rejection reason is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        if testimonial.status == TestimonialStatus.REJECTED:
            return Response(
                {"detail": _("Testimonial is already rejected.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reject the testimonial
        testimonial.status = TestimonialStatus.REJECTED
        testimonial.rejection_reason = rejection_reason
        testimonial.save(update_fields=['status', 'rejection_reason'])

        # Background email notification
        if app_settings.USE_CELERY and testimonial.author_email:
            try:
                from ..tasks import send_testimonial_email
                execute_task(
                    send_testimonial_email,
                    str(testimonial.pk),
                    'rejected',
                    testimonial.author_email,
                    {'reason': rejection_reason}
                )
            except Exception as e:
                log_testimonial_action(testimonial, "rejection_email_failed", 
                                     request.user, str(e))

        # Log the rejection
        log_testimonial_action(testimonial, "reject", request.user, notes=rejection_reason)

        # Invalidate cache
        invalidate_testimonial_cache(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def feature(self, request, pk=None):
        """
        Feature a testimonial with cache invalidation.
        """
        if not self.is_moderator_or_admin(request.user):
            return Response(
                {"detail": _("You do not have permission to feature testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )

        testimonial = self.get_object()

        if testimonial.status == TestimonialStatus.FEATURED:
            return Response(
                {"detail": _("Testimonial is already featured.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        testimonial.status = TestimonialStatus.FEATURED
        testimonial.save(update_fields=['status'])

        log_testimonial_action(testimonial, "feature", request.user)

        # Invalidate featured testimonials cache specifically
        if app_settings.USE_REDIS_CACHE:
            cache.delete(get_cache_key('featured_testimonials'))
            cache.delete(get_cache_key('featured_testimonials_api'))

        invalidate_testimonial_cache(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive a testimonial with cleanup.
        """
        if not self.is_moderator_or_admin(request.user):
            return Response(
                {"detail": _("You do not have permission to archive testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )

        testimonial = self.get_object()

        if testimonial.status == TestimonialStatus.ARCHIVED:
            return Response(
                {"detail": _("Testimonial is already archived.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        testimonial.status = TestimonialStatus.ARCHIVED
        testimonial.save(update_fields=['status'])

        log_testimonial_action(testimonial, "archive", request.user)

        # Invalidate cache
        invalidate_testimonial_cache(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """
        Add a response to a testimonial with background email.
        """
        testimonial = self.get_object()
        response_text = request.data.get('response', '').strip()
        
        if not response_text:
            return Response(
                {"detail": _("Response text is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        testimonial.response = response_text
        testimonial.response_at = timezone.now()
        testimonial.response_by = request.user
        testimonial.save(update_fields=['response', 'response_at', 'response_by'])
        
        # Background email notification
        if app_settings.USE_CELERY and testimonial.author_email:
            try:
                from ..tasks import send_testimonial_email
                execute_task(
                    send_testimonial_email,
                    str(testimonial.pk),
                    'response',
                    testimonial.author_email,
                    {'response': response_text}
                )
            except Exception as e:
                log_testimonial_action(testimonial, "response_email_failed", 
                                     request.user, str(e))
        
        # Log the action
        log_testimonial_action(testimonial, "respond", request.user)
        
        # Invalidate cache
        invalidate_testimonial_cache(testimonial_id=testimonial.pk)
        
        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_media(self, request, pk=None):
        """
        Add media to a testimonial with background processing.
        """
        testimonial = self.get_object()
        file_obj = request.data.get('file')
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        
        if not file_obj:
            return Response(
                {"detail": _("File is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create media
        media = testimonial.add_media(file_obj, title, description)
        
        # Background processing
        if app_settings.USE_CELERY:
            try:
                from ..tasks import process_media
                execute_task(process_media, str(media.pk))
            except Exception as e:
                log_testimonial_action(testimonial, "media_processing_failed", 
                                     request.user, str(e))
        
        # Invalidate cache
        invalidate_testimonial_cache(testimonial_id=testimonial.pk)
        
        serializer = TestimonialMediaSerializer(media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Optimized bulk moderation with background processing.
        """
        if not self.is_moderator_or_admin(request.user):
            return Response(
                {"detail": _("You do not have permission to perform bulk actions.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        action_type = request.data.get('action')
        
        if action_type not in ['approve', 'reject', 'feature', 'archive']:
            return Response(
                {"detail": _("Invalid action. Must be one of: approve, reject, feature, archive.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TestimonialAdminActionSerializer(
            data=request.data,
            context={'action': action_type}
        )
        serializer.is_valid(raise_exception=True)
        
        testimonial_ids = serializer.validated_data['testimonial_ids']
        
        # Process in background if Celery is available for large operations
        if app_settings.USE_CELERY and len(testimonial_ids) > 10:
            try:
                from ..tasks import bulk_moderate
                task = execute_task(
                    bulk_moderate,
                    testimonial_ids,
                    action_type,
                    request.user.id,
                    serializer.validated_data
                )
                
                return Response({
                    "detail": _("Bulk action queued for processing."),
                    "task_id": getattr(task, 'id', None),
                    "count": len(testimonial_ids)
                })
            except Exception as e:
                # Fall back to synchronous processing
                pass
        
        # Synchronous processing for small operations or fallback
        testimonials = Testimonial.objects.filter(pk__in=testimonial_ids)
        processed_count = 0
        
        for testimonial in testimonials:
            if action_type == 'approve':
                testimonial.status = TestimonialStatus.APPROVED
                testimonial.approved_at = timezone.now()
                testimonial.approved_by = request.user
                
            elif action_type == 'reject':
                testimonial.status = TestimonialStatus.REJECTED
                if 'rejection_reason' in serializer.validated_data:
                    testimonial.rejection_reason = serializer.validated_data['rejection_reason']
                
            elif action_type == 'feature':
                testimonial.status = TestimonialStatus.FEATURED
                
            elif action_type == 'archive':
                testimonial.status = TestimonialStatus.ARCHIVED
            
            testimonial.save()
            processed_count += 1
            
            # Log individual action
            log_testimonial_action(testimonial, f"bulk_{action_type}", request.user)
        
        # Invalidate all relevant cache
        invalidate_testimonial_cache()
        
        return Response({
            "detail": _("Successfully processed %(count)d testimonials.") % {'count': processed_count},
            "count": processed_count
        })


class TestimonialCategoryViewSet(viewsets.ModelViewSet):
    """
    Optimized API endpoint for testimonial categories.
    """
    queryset = TestimonialCategory.objects.all()
    serializer_class = TestimonialCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order', 'created_at']
    ordering = ['order', 'name']
    
    def get_queryset(self):
        """
        Optimized queryset with permission-based filtering.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
            queryset = queryset.active()
        
        return queryset.with_testimonials_count()
    
    @method_decorator(cache_page(app_settings.CACHE_TIMEOUT))
    def list(self, request, *args, **kwargs):
        """
        Cached category list.
        """
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def testimonials(self, request, pk=None):
        """
        Optimized testimonials for a specific category.
        """
        category = self.get_object()
        
        def get_category_testimonials():
            # FIXED: Use proper queryset method
            testimonials = Testimonial.objects.filter(category=category).optimized_for_api()
            
            # Apply permission filtering
            user = request.user
            if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
                testimonials = testimonials.published()
            
            # Use the testimonial viewset pagination
            testimonial_viewset = TestimonialViewSet()
            testimonial_viewset.request = request
            testimonial_viewset.format_kwarg = self.format_kwarg
            
            page = testimonial_viewset.paginate_queryset(testimonials)
            if page is not None:
                serializer = TestimonialSerializer(page, many=True, context={'request': request})
                return testimonial_viewset.get_paginated_response(serializer.data)
            
            serializer = TestimonialSerializer(testimonials, many=True, context={'request': request})
            return Response(serializer.data)
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('category_testimonials', category.pk, 
                                    'admin' if request.user.is_staff else 'public')
            return cache_get_or_set(cache_key, get_category_testimonials)
        
        return get_category_testimonials()


class TestimonialMediaViewSet(viewsets.ModelViewSet):
    """
    Optimized API endpoint for testimonial media.
    """
    queryset = TestimonialMedia.objects.all()
    serializer_class = TestimonialMediaSerializer
    permission_classes = [IsTestimonialAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['testimonial', 'media_type', 'is_primary']
    ordering_fields = ['order', 'created_at']
    ordering = ['-is_primary', 'order', '-created_at']
    
    def get_queryset(self):
        """
        Optimized queryset with permission filtering and prefetching.
        """
        # FIXED: Use proper queryset method
        queryset = TestimonialMedia.objects.optimized_for_api()
        user = self.request.user
        
        # Check admin/moderator permissions
        if self.is_moderator_or_admin(user):
            return queryset
        elif user.is_authenticated:
            # Users see media for published testimonials and their own
            return queryset.filter(
                Q(testimonial__status__in=TestimonialStatus.get_published_statuses()) |
                Q(testimonial__author=user)
            )
        else:
            # Anonymous users see only media for published testimonials
            return queryset.filter(
                testimonial__status__in=TestimonialStatus.get_published_statuses()
            )
    
    def is_moderator_or_admin(self, user):
        """
        Check if user is moderator or admin.
        """
        return (user.is_authenticated and 
                (user.is_staff or user.is_superuser or 
                 (hasattr(user, 'groups') and 
                  user.groups.filter(name__in=app_settings.MODERATION_ROLES).exists())))
    
    def create(self, request, *args, **kwargs):
        """
        Create media with background processing.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        media = serializer.save()
        
        # Background processing
        if app_settings.USE_CELERY:
            try:
                from ..tasks import process_media
                execute_task(process_media, str(media.pk))
            except Exception as e:
                log_testimonial_action(media.testimonial, "media_processing_failed", 
                                     request.user, str(e))
        
        # Invalidate cache
        invalidate_testimonial_cache(testimonial_id=media.testimonial_id)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete media with cache invalidation.
        """
        instance = self.get_object()
        testimonial_id = instance.testimonial_id
        
        # Log deletion
        log_testimonial_action(instance.testimonial, "media_delete", request.user)
        
        self.perform_destroy(instance)
        
        # Invalidate cache
        invalidate_testimonial_cache(testimonial_id=testimonial_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def by_testimonial(self, request):
        """
        Optimized media retrieval by testimonial with caching.
        """
        testimonial_id = request.query_params.get('testimonial_id')
        if not testimonial_id:
            return Response(
                {"detail": _("testimonial_id query parameter is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            testimonial = Testimonial.objects.select_related('author').get(pk=testimonial_id)
        except Testimonial.DoesNotExist:
            return Response(
                {"detail": _("Testimonial not found.")},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        user = request.user
        has_permission = (
            self.is_moderator_or_admin(user) or
            (user.is_authenticated and testimonial.author == user) or
            testimonial.is_published
        )
        
        if not has_permission:
            return Response(
                {"detail": _("You do not have permission to view this testimonial's media.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        def get_testimonial_media():
            media = self.get_queryset().filter(testimonial=testimonial)
            page = self.paginate_queryset(media)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(media, many=True)
            return Response(serializer.data)
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('testimonial_media', testimonial_id, user.id if user.is_authenticated else 'anon')
            return cache_get_or_set(cache_key, get_testimonial_media, 
                                  timeout=app_settings.CACHE_TIMEOUT // 2)
        
        return get_testimonial_media()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Cached media statistics.
        """
        def get_media_stats():
            return Response(TestimonialMedia.objects.get_media_stats())
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('media_stats')
            return cache_get_or_set(cache_key, get_media_stats, 
                                  timeout=app_settings.CACHE_TIMEOUT * 2)
        
        return get_media_stats()


# === PERFORMANCE MONITORING MIDDLEWARE ===

class PerformanceMonitoringMixin:
    """
    Mixin to add performance monitoring to API views.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        Monitor API performance and log slow requests.
        """
        import time
        start_time = time.time()
        
        response = super().dispatch(request, *args, **kwargs)
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Log slow requests
        if duration > 1000:  # More than 1 second
            log_testimonial_action(
                None,
                "slow_api_request",
                request.user if hasattr(request, 'user') else None,
                f"Slow request: {request.method} {request.path}",
                {
                    'duration_ms': duration,
                    'view': self.__class__.__name__,
                    'action': getattr(self, 'action', request.method.lower()),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'query_count': getattr(response, 'query_count', 0)
                }
            )
        
        # Add performance headers
        response['X-Response-Time'] = f"{duration:.2f}ms"
        
        return response


# === ENHANCED VIEWSETS WITH MONITORING ===

class EnhancedTestimonialViewSet(PerformanceMonitoringMixin, TestimonialViewSet):
    """
    TestimonialViewSet with performance monitoring.
    """
    pass


class EnhancedTestimonialCategoryViewSet(PerformanceMonitoringMixin, TestimonialCategoryViewSet):
    """
    TestimonialCategoryViewSet with performance monitoring.
    """
    pass


class EnhancedTestimonialMediaViewSet(PerformanceMonitoringMixin, TestimonialMediaViewSet):
    """
    TestimonialMediaViewSet with performance monitoring.
    """
    pass