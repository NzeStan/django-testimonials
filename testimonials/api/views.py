from rest_framework import viewsets, permissions, filters, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus
from ..conf import app_settings
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


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API results."""
    page_size = app_settings.PAGINATION_SIZE
    page_size_query_param = 'page_size'
    max_page_size = 100


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    API endpoint for testimonials.
    
    list:
        Return a list of all published testimonials.
    
    create:
        Create a new testimonial.
    
    retrieve:
        Return a specific testimonial.
    
    update:
        Update a specific testimonial.
    
    partial_update:
        Partially update a specific testimonial.
    
    destroy:
        Delete a specific testimonial.
    """
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TestimonialFilter
    search_fields = ['author_name', 'company', 'content', 'title']
    ordering_fields = ['created_at', 'rating', 'display_order']
    ordering = ['-display_order', '-created_at']
    
    def get_queryset(self):
        """
        Return the appropriate queryset based on user permissions.
        
        - Admins and moderators see all testimonials
        - Authors see their own testimonials
        - Everyone else sees only published testimonials
        """
        user = self.request.user
        
        # Base queryset with related objects for optimization
        queryset = super().get_queryset().select_related(
            'category', 'author', 'approved_by'
        ).prefetch_related('media')
        
        # Check admin/moderator permissions
        is_admin = user.is_authenticated and (user.is_staff or user.is_superuser)
        is_moderator = user.is_authenticated and hasattr(user, 'groups') and user.groups.filter(
            name__in=app_settings.MODERATION_ROLES
        ).exists()
        
        # Filter based on permissions
        if is_admin or is_moderator:
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
            return queryset.filter(
                status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
            )
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer based on the action.
        """
        if self.action == 'create':
            return TestimonialCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return TestimonialDetailSerializer
        return TestimonialSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsTestimonialAuthorOrReadOnly()]
        elif self.action in ['moderate', 'approve', 'reject', 'feature', 'archive']:
            return [CanModerateTestimonial()]
        elif self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    
    def perform_create(self, serializer):
        """
        Perform custom actions when creating a testimonial.
        
        Set the author if authenticated.
        """
        user = self.request.user
        if user.is_authenticated:
            serializer.save(author=user)
        else:
            serializer.save()
    
    def is_moderator(self, user):
        return user.is_authenticated and (
            user.is_staff or 
            user.is_superuser or 
            (hasattr(user, 'groups') and user.groups.filter(name__in=app_settings.MODERATION_ROLES).exists())
        )


    @action(detail=False, methods=['get'])
    def mine(self, request):
        """
        Return testimonials created by the current user.
        """
        if not request.user.is_authenticated:
            return Response(
                {"detail": _("Authentication required to view your testimonials.")},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        testimonials = self.queryset.filter(author=request.user)
        page = self.paginate_queryset(testimonials)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(testimonials, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Return pending testimonials (for moderators).
        """
        
        # Check permissions
        if not self.is_moderator(request.user):
            return Response(
                {"detail": _("You do not have permission to reject testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        testimonials = self.queryset.filter(status=TestimonialStatus.PENDING)
        page = self.paginate_queryset(testimonials)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(testimonials, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a testimonial (moderators only).
        """
        user = request.user  # ✅ Define user

        if not self.is_moderator(user):
            return Response(
                {"detail": _("You do not have permission to approve testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the testimonial instance
        testimonial = self.get_object()

        # Check if already approved
        if testimonial.status == TestimonialStatus.APPROVED:
            return Response(
                {"detail": _("Testimonial is already approved.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Approve the testimonial
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.approved_at = timezone.now()
        testimonial.approved_by = user
        testimonial.save()

        # Log the approval
        log_testimonial_action(testimonial, "approve", user)

        # Serialize and return the response
        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)

    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a testimonial (moderators only).
        """
        if not self.is_moderator(request.user):
            return Response(
                {"detail": _("You do not have permission to reject testimonials.")},
                status=status.HTTP_403_FORBIDDEN
            )

        testimonial = self.get_object()

        rejection_reason = request.data.get('rejection_reason', '')
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

        testimonial.status = TestimonialStatus.REJECTED
        testimonial.rejection_reason = rejection_reason
        testimonial.save()

        log_testimonial_action(testimonial, "reject", request.user, notes=rejection_reason)

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)

    
    @action(detail=True, methods=['post'])
    def feature(self, request, pk=None):
        """
        Feature a testimonial (moderators only).
        """
        if not self.is_moderator(request.user):
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
        testimonial.save()

        log_testimonial_action(testimonial, "feature", request.user)

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)

    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive a testimonial (moderators only).
        """
        if not self.is_moderator(request.user):
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
        testimonial.save()

        log_testimonial_action(testimonial, "archive", request.user)

        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)

    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """
        Add a response to a testimonial.
        """
        testimonial = self.get_object()
        
        # Get response from request data
        response_text = request.data.get('response', '')
        
        if not response_text:
            return Response(
                {"detail": _("Response text is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        testimonial.response = response_text
        testimonial.response_at = timezone.now()
        testimonial.response_by = request.user
        testimonial.save()
        
        # Log the action
        log_testimonial_action(testimonial, "respond", request.user)
        
        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_media(self, request, pk=None):
        """
        Add media to a testimonial.
        """
        testimonial = self.get_object()
        
        # Get file from request data
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
        
        serializer = TestimonialMediaSerializer(media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def moderate(self, request):
        """
        Bulk moderate testimonials.
        
        Expected payload:
        {
            "action": "approve|reject|feature|archive",
            "testimonial_ids": [1, 2, 3],
            "rejection_reason": "Optional reason for rejection"
        }
        """
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
        testimonials = Testimonial.objects.filter(pk__in=testimonial_ids)
        
        # Perform the action on all testimonials
        if action_type == 'approve':
            for testimonial in testimonials:
                testimonial.status = TestimonialStatus.APPROVED
                testimonial.approved_at = timezone.now()
                testimonial.approved_by = request.user
                testimonial.save()
                log_testimonial_action(testimonial, "approve", request.user)
        
        elif action_type == 'reject':
            rejection_reason = serializer.validated_data.get('rejection_reason', '')
            for testimonial in testimonials:
                testimonial.status = TestimonialStatus.REJECTED
                testimonial.rejection_reason = rejection_reason
                testimonial.save()
                log_testimonial_action(testimonial, "reject", request.user, notes=rejection_reason)
        
        elif action_type == 'feature':
            for testimonial in testimonials:
                testimonial.status = TestimonialStatus.FEATURED
                testimonial.save()
                log_testimonial_action(testimonial, "feature", request.user)
        
        elif action_type == 'archive':
            for testimonial in testimonials:
                testimonial.status = TestimonialStatus.ARCHIVED
                testimonial.save()
                log_testimonial_action(testimonial, "archive", request.user)
        
        return Response({
            "detail": _("Successfully moderated %(count)d testimonials.") % {'count': testimonials.count()},
            "count": testimonials.count()
        })


class TestimonialCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for testimonial categories.
    """
    queryset = TestimonialCategory.objects.all()
    serializer_class = TestimonialCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order']
    ordering = ['order', 'name']
    
    def get_queryset(self):
        """
        Return only active categories for non-admin users.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def testimonials(self, request, pk=None):
        """
        Return testimonials for a specific category.
        """
        category = self.get_object()
        testimonials = Testimonial.objects.filter(category=category)
        
        # Apply the same filtering as the main testimonial viewset
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            testimonials = testimonials.filter(
                status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
            )
        
        page = self.paginate_queryset(testimonials)
        if page is not None:
            serializer = TestimonialSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = TestimonialSerializer(testimonials, many=True, context={'request': request})
        return Response(serializer.data)


class TestimonialMediaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for testimonial media.
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
        Return media for published testimonials and user's own testimonials.
        """
        queryset = super().get_queryset().select_related('testimonial')
        user = self.request.user
        
        # Check admin/moderator permissions
        is_admin = user.is_authenticated and (user.is_staff or user.is_superuser)
        is_moderator = user.is_authenticated and hasattr(user, 'groups') and user.groups.filter(
            name__in=app_settings.MODERATION_ROLES
        ).exists()
        
        # Filter based on permissions
        if is_admin or is_moderator:
            # Admins and moderators see everything
            return queryset
        elif user.is_authenticated:
            # Authenticated users see media for published testimonials and their own
            return queryset.filter(
                Q(testimonial__status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]) |
                Q(testimonial__author=user)
            )
        else:
            # Anonymous users see only media for published testimonials
            return queryset.filter(
                testimonial__status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
            )
    
    @action(detail=False, methods=['get'])
    def by_testimonial(self, request):
        """
        Return media for a specific testimonial.
        """
        testimonial_id = request.query_params.get('testimonial_id')
        if not testimonial_id:
            return Response(
                {"detail": _("testimonial_id query parameter is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if the testimonial exists and if the user has permission to see it
            testimonial = Testimonial.objects.get(pk=testimonial_id)
        except Testimonial.DoesNotExist:
            return Response(
                {"detail": _("Testimonial not found.")},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        user = request.user
        is_admin = user.is_authenticated and (user.is_staff or user.is_superuser)
        is_moderator = user.is_authenticated and hasattr(user, 'groups') and user.groups.filter(
            name__in=app_settings.MODERATION_ROLES
        ).exists()
        is_author = user.is_authenticated and testimonial.author == user
        
        if not (is_admin or is_moderator or is_author or testimonial.is_published):
            return Response(
                {"detail": _("You do not have permission to view this testimonial's media.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        media = self.queryset.filter(testimonial=testimonial)
        
        page = self.paginate_queryset(media)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(media, many=True)
        return Response(serializer.data)