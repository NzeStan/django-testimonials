# testimonials/dashboard/urls.py

from django.urls import path
from . import views

app_name = 'testimonials-dashboard'

urlpatterns = [
    path('', views.dashboard_overview, name='overview'),
    path('analytics/', views.dashboard_analytics, name='analytics'),
    path('moderation/', views.dashboard_moderation, name='moderation'),
    path('categories/', views.dashboard_categories, name='categories'),
]