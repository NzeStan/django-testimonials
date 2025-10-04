# testimonials/urls.py - UPDATED WITH DASHBOARD

from django.urls import path, include
from django.conf import settings
from .conf import app_settings

app_name = 'testimonials'

urlpatterns = [
    # API endpoints
    path('api/', include('testimonials.api.urls', namespace='api')),
]

# ✅ Include dashboard URLs if enabled
if app_settings.ENABLE_DASHBOARD:
    urlpatterns += [
        path('dashboard/', include('testimonials.dashboard.urls', namespace='dashboard')),
    ]