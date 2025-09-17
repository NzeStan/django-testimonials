from django.urls import path, include
from django.conf import settings
from .conf import app_settings
app_name = 'testimonials'

urlpatterns = [
    # API endpoints
    path('api/', include('testimonials.api.urls', namespace='api')),
]

# Optional: Include admin dashboard URLs if enabled
if app_settings.ENABLE_DASHBOARD:
    from .admin import testimonial_dashboard
    
    urlpatterns += [
        path('dashboard/', testimonial_dashboard.urls),
    ]