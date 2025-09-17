from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TestimonialViewSet,
    TestimonialCategoryViewSet,
    TestimonialMediaViewSet
)

app_name = 'testimonials-api'

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'testimonials', TestimonialViewSet)
router.register(r'categories', TestimonialCategoryViewSet)
router.register(r'media', TestimonialMediaViewSet)

# URL patterns
urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
]