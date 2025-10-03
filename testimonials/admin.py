from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import render
from .models import Testimonial, TestimonialCategory, TestimonialMedia
from .forms import TestimonialAdminForm, TestimonialCategoryForm, TestimonialMediaForm
from .constants import TestimonialStatus
from .constants import TestimonialMediaType


class TestimonialMediaInline(admin.TabularInline):
    """
    Inline admin for testimonial media.
    """
    model = TestimonialMedia
    form = TestimonialMediaForm
    extra = 1
    fields = ('file', 'media_type', 'title', 'is_primary', 'order')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-is_primary', 'order')


@admin.register(TestimonialCategory)
class TestimonialCategoryAdmin(admin.ModelAdmin):
    """
    Admin for testimonial categories.
    """
    form = TestimonialCategoryForm
    list_display = ('name', 'slug', 'is_active', 'testimonials_count', 'order')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        (_('Settings'), {
            'fields': ('is_active', 'order')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def testimonials_count(self, obj):
        """Count of testimonials in this category."""
        count = getattr(obj, 'testimonials_count', None)
        if count is None:
            count = obj.testimonials.count()
        return count
    testimonials_count.short_description = _('Testimonials')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(testimonials_count=Count('testimonials'))


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    """
    Admin for testimonials.
    """
    form = TestimonialAdminForm
    list_display = ('get_avatar_thumbnail','author_name', 'company', 'get_rating_stars', 'status_badge', 'category', 'created_at_formatted', 'has_media')
    list_filter = ('status', 'rating', 'category', 'created_at', 'is_anonymous', 'is_verified')
    search_fields = ('author_name', 'author_email', 'company', 'content')
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'ip_address', 'get_avatar_preview')
    actions = ['approve_testimonials', 'reject_testimonials', 'feature_testimonials', 'archive_testimonials']
    inlines = [TestimonialMediaInline]
    
    fieldsets = (
        (_('Author Information'), {
            'fields': (
                'author', 'author_name', 'author_email', 'author_phone', 
                'author_title', 'company', 'location', 'avatar'
            )
        }),
        (_('Testimonial Content'), {
            'fields': ('title', 'content', 'rating', 'response', 'response_at', 'response_by')
        }),
        (_('Categorization'), {
            'fields': ('category', 'source')
        }),
        (_('Status and Moderation'), {
            'fields': (
                'status', 'is_anonymous', 'is_verified', 'display_order',
                'approved_at', 'approved_by', 'rejection_reason'
            )
        }),
        (_('Additional Information'), {
            'fields': ('slug', 'website', 'social_media', 'ip_address', 'extra_data'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'author', 'approved_by')
    
    def get_rating_stars(self, obj):
        """Display rating as stars."""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span title="{}">{}</span>', obj.rating, stars)
    get_rating_stars.short_description = _('Rating')
    
    def status_badge(self, obj):
        """Display status as a colored badge."""
        status_colors = {
            TestimonialStatus.PENDING: '#f8c291',   # Orange
            TestimonialStatus.APPROVED: '#7bed9f',  # Green
            TestimonialStatus.REJECTED: '#ff6b6b',  # Red
            TestimonialStatus.FEATURED: '#70a1ff',  # Blue
            TestimonialStatus.ARCHIVED: '#a4b0be',  # Grey
        }
        
        color = status_colors.get(obj.status, '#a4b0be')
        status_display = dict(TestimonialStatus.choices).get(obj.status, obj.status)
        
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: #fff;">{}</span>',
            color,
            status_display
        )
    status_badge.short_description = _('Status')
    
    def has_media(self, obj):
        """Check if testimonial has media."""
        return obj.media.exists()
    has_media.boolean = True
    has_media.short_description = _('Media')
    
    def created_at_formatted(self, obj):
        """Format the creation date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = _('Created at')
    created_at_formatted.admin_order_field = 'created_at'
    
    def approve_testimonials(self, request, queryset):
        """Admin action to approve testimonials."""
        updated = 0
        for testimonial in queryset:
            if testimonial.status != TestimonialStatus.APPROVED:
                testimonial.status = TestimonialStatus.APPROVED
                testimonial.approved_at = timezone.now()
                testimonial.approved_by = request.user
                testimonial.save()
                updated += 1
        
        messages.success(request, _('%(count)d testimonials were approved.') % {'count': updated})
    approve_testimonials.short_description = _('Approve selected testimonials')
    

    def reject_testimonials(self, request, queryset):
        """
        Admin action to reject testimonials.
        FIXED: Skip Django's default confirmation to avoid double confirmation.
        """
        # Check if we're processing the final form submission
        if 'apply' in request.POST:
            rejection_reason = request.POST.get('rejection_reason', '')
            updated = 0
            
            for testimonial in queryset:
                if testimonial.status != TestimonialStatus.REJECTED:
                    testimonial.status = TestimonialStatus.REJECTED
                    testimonial.rejection_reason = rejection_reason
                    testimonial.save()
                    updated += 1
            
            messages.success(request, _('%(count)d testimonials were rejected.') % {'count': updated})
            return HttpResponseRedirect(request.get_full_path())
        
        # ✅ CRITICAL FIX: Check if this is the first call (from action dropdown)
        # If '_selected_action' is in POST but 'apply' is not, show our custom form
        # This skips Django's default intermediate confirmation page
        if request.POST.get('_selected_action'):
            # This is the first submission from selecting the action
            # Go directly to our custom rejection form (skip Django's default confirmation)
            context = {
                'title': _('Enter rejection reason'),
                'queryset': queryset,
                'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
                'action': 'reject_testimonials',
                'opts': self.model._meta,
            }
            
            return render(request, 'testimonials/admin/testimonials/reject_testimonials.html', context)
        
        # This shouldn't happen, but just in case
        return None

    reject_testimonials.short_description = _('Reject selected testimonials')
    
    def feature_testimonials(self, request, queryset):
        """Admin action to feature testimonials."""
        updated = 0
        for testimonial in queryset:
            if testimonial.status != TestimonialStatus.FEATURED:
                testimonial.status = TestimonialStatus.FEATURED
                testimonial.save()
                updated += 1
        
        messages.success(request, _('%(count)d testimonials were featured.') % {'count': updated})
    feature_testimonials.short_description = _('Feature selected testimonials')
    
    def archive_testimonials(self, request, queryset):
        """Admin action to archive testimonials."""
        updated = 0
        for testimonial in queryset:
            if testimonial.status != TestimonialStatus.ARCHIVED:
                testimonial.status = TestimonialStatus.ARCHIVED
                testimonial.save()
                updated += 1
        
        messages.success(request, _('%(count)d testimonials were archived.') % {'count': updated})
    archive_testimonials.short_description = _('Archive selected testimonials')

    def get_avatar_thumbnail(self, obj):
        """Display a small avatar thumbnail in list view."""
        if obj.avatar:
            return format_html(
                '<img src="{}" width="40" height="40" style="object-fit: cover; border-radius: 50%;" />',
                obj.avatar.url
            )
        else:
            # Show placeholder for missing avatar
            return format_html(
                '<div style="width: 40px; height: 40px; border-radius: 50%; '
                'background-color: #e0e0e0; display: flex; align-items: center; '
                'justify-content: center; font-size: 18px;">👤</div>'
            )
    get_avatar_thumbnail.short_description = _('Avatar')
    
    def get_avatar_preview(self, obj):
        """Display a larger avatar preview in detail view."""
        if obj.avatar:
            return format_html(
                '<div style="margin: 10px 0;">'
                '<img src="{}" style="max-width: 200px; max-height: 200px; '
                'border-radius: 8px; object-fit: cover;" />'
                '</div>',
                obj.avatar.url
            )
        else:
            return format_html(
                '<div style="width: 200px; height: 200px; border-radius: 8px; '
                'background-color: #f5f5f5; display: flex; align-items: center; '
                'justify-content: center; font-size: 72px; border: 2px dashed #ccc;">👤</div>'
            )
    get_avatar_preview.short_description = _('Avatar Preview')
    
    def save_model(self, request, obj, form, change):
        """Override save_model to handle special cases."""
        # Set approved_by and approved_at when status changes to approved
        if change and form.initial.get('status') != TestimonialStatus.APPROVED and obj.status == TestimonialStatus.APPROVED:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
        
        # Set response_by and response_at when a response is added
        if form.cleaned_data.get('response') and not obj.response_by:
            obj.response_by = request.user
            obj.response_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        """Override get_form to pass additional context."""
        form = super().get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form
    
    class Media:
        css = {
            'all': ('testimonials/css/admin.css',)
        }
        js = ('testimonials/js/admin.js',)


@admin.register(TestimonialMedia)
class TestimonialMediaAdmin(admin.ModelAdmin):
    """
    Admin for testimonial media.
    """
    list_display = ('get_thumbnail', 'testimonial', 'media_type', 'is_primary', 'order', 'created_at_formatted')
    list_filter = ('media_type', 'is_primary', 'created_at')
    search_fields = ('title', 'description', 'testimonial__author_name')
    readonly_fields = ('created_at', 'updated_at', 'get_preview')
    raw_id_fields = ('testimonial',)
    
    fieldsets = (
        (None, {
            'fields': ('testimonial', 'file', 'media_type')
        }),
        (_('Details'), {
            'fields': ('title', 'description', 'is_primary', 'order')
        }),
        (_('Preview'), {
            'fields': ('get_preview',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_thumbnail(self, obj):
        """Display a thumbnail preview for the media."""
        if not obj.file:
            return '-'
        
        # FIXED: Use the actual media_type value, not string comparison
        if obj.media_type == TestimonialMediaType.IMAGE:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', 
                obj.file.url
            )
        elif obj.media_type == TestimonialMediaType.VIDEO:
            return format_html('<span class="video-thumbnail" style="font-size: 30px;">🎬</span>')
        elif obj.media_type == TestimonialMediaType.AUDIO:
            return format_html('<span class="audio-thumbnail" style="font-size: 30px;">🔊</span>')
        elif obj.media_type == TestimonialMediaType.DOCUMENT:
            return format_html('<span class="document-thumbnail" style="font-size: 30px;">📄</span>')
        else:
            return format_html('<span style="font-size: 30px;">📎</span>')

    get_thumbnail.short_description = _('Thumbnail')
    
    def get_preview(self, obj):
        """Display a preview for the media."""
        if obj.media_type == 'image':
            return format_html('<img src="{}" style="max-width: 100%; max-height: 300px;" />', obj.file.url)
        elif obj.media_type == 'video':
            return format_html('<video controls style="max-width: 100%; max-height: 300px;"><source src="{}" /></video>', obj.file.url)
        elif obj.media_type == 'audio':
            return format_html('<audio controls><source src="{}" /></audio>', obj.file.url)
        else:
            return format_html('<a href="{}" target="_blank" class="button">View Document</a>', obj.file.url)
    get_preview.short_description = _('Preview')
    
    def created_at_formatted(self, obj):
        """Format the creation date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = _('Created at')
    created_at_formatted.admin_order_field = 'created_at'
    
    class Media:
        css = {
            'all': ('testimonials/css/admin.css',)
        }


# Register with admin site
from django.contrib.admin import site

# Add admin dashboard panel for testimonials
class TestimonialDashboard(admin.AdminSite):
    """Custom admin site for testimonials dashboard."""
    site_header = _('Testimonials Dashboard')
    site_title = _('Testimonials Dashboard')
    index_title = _('Dashboard')

# Only register if explicitly enabled in settings
from .conf import app_settings
if app_settings.ENABLE_DASHBOARD:
    testimonial_dashboard = TestimonialDashboard(name='testimonial_dashboard')
    testimonial_dashboard.register(Testimonial, TestimonialAdmin)
    testimonial_dashboard.register(TestimonialCategory, TestimonialCategoryAdmin)
    testimonial_dashboard.register(TestimonialMedia, TestimonialMediaAdmin)

# Import render for the reject_testimonials action
