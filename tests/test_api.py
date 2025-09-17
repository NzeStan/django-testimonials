"""
Tests for the testimonials app API.
"""

import pytest
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from testimonials.models import Testimonial, TestimonialCategory
from testimonials.constants import TestimonialStatus


@pytest.mark.django_db
class TestTestimonialAPI:
    """Tests for the Testimonial API endpoints."""
    
    def test_list_testimonials(self, api_client, testimonial, pending_testimonial, featured_testimonial):
        """Test listing testimonials API endpoint."""
        url = reverse('testimonials-api:testimonial-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check correct pagination structure
        assert 'count' in data
        assert 'results' in data
        
        # Check that only published testimonials are returned for anonymous users
        assert data['count'] == 2
        
        # Verify ids of returned testimonials
        result_ids = [t['id'] for t in data['results']]
        assert str(testimonial.id) in result_ids
        assert str(featured_testimonial.id) in result_ids
        assert str(pending_testimonial.id) not in result_ids
    
    def test_get_testimonial_detail(self, api_client, testimonial):
        """Test retrieving a single testimonial."""
        url = reverse('testimonials-api:testimonial-detail', args=[testimonial.id])
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data['id'] == str(testimonial.id)
        assert data['author_name'] == testimonial.author_name
        assert data['content'] == testimonial.content
        assert data['rating'] == testimonial.rating
    
    def test_create_testimonial(self, api_client, category):
        """Test creating a testimonial via the API."""
        url = reverse('testimonials-api:testimonial-list')
        data = {
            'author_name': 'API Test User',
            'author_email': 'apitest@example.com',
            'content': 'This testimonial was created via the API.',
            'rating': 5,
            'category_id': category.id
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check the created testimonial
        testimonial_id = response.json()['id']
        testimonial = Testimonial.objects.get(id=testimonial_id)
        
        assert testimonial.author_name == 'API Test User'
        assert testimonial.content == 'This testimonial was created via the API.'
        assert testimonial.rating == 5
        assert testimonial.category_id == category.id
        assert testimonial.status == TestimonialStatus.PENDING  # Should be pending by default
    
    def test_create_anonymous_testimonial(self, api_client, category):
        """Test creating an anonymous testimonial."""
        url = reverse('testimonials-api:testimonial-list')
        data = {
            'content': 'This is an anonymous testimonial created via API.',
            'rating': 4,
            'category_id': category.id,
            'is_anonymous': True
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check the created testimonial
        testimonial_id = response.json()['id']
        testimonial = Testimonial.objects.get(id=testimonial_id)
        
        assert testimonial.is_anonymous is True
        assert testimonial.author_name == 'Anonymous'
        assert testimonial.author_email == ''
        assert testimonial.author is None
    
    def test_authenticated_user_permissions(self, api_client, user, testimonial, pending_testimonial):
        """Test permissions for authenticated users."""
        # Login the user
        api_client.force_authenticate(user=user)
        
        # User should be able to see their own pending testimonials
        url = reverse('testimonials-api:testimonial-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Count should include published and user's own
        assert data['count'] >= 2
        
        # Should include user's pending testimonial
        result_ids = [t['id'] for t in data['results']]
        assert str(pending_testimonial.id) in result_ids
        
        # Test updating