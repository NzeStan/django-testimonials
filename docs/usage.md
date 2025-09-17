# Usage Guide

This guide provides examples and best practices for using Django Testimonials in your Django project.

## Basic Usage

Django Testimonials provides both a model API and a REST API. Here's how to use them.

### Working with Testimonials (Model API)

```python
from testimonials.models import Testimonial, TestimonialCategory

# Create a category
category = TestimonialCategory.objects.create(
    name="Product Feedback",
    description="Testimonials about our products",
    is_active=True
)

# Create a testimonial
testimonial = Testimonial.objects.create(
    author_name="John Doe",
    author_email="john@example.com",
    content="This product is amazing! It saved me hours of work.",
    rating=5,
    category=category,
    status="approved"  # Or use TestimonialStatus.APPROVED
)

# Get all published testimonials (approved or featured)
published_testimonials = Testimonial.objects.published()

# Get testimonials with a high rating
high_rated = Testimonial.objects.with_rating(min_rating=4)

# Get testimonials for a specific category
category_testimonials = Testimonial.objects.with_category(category_slug="product-feedback")

# Search testimonials
search_results = Testimonial.objects.search("amazing product")

# Approve a testimonial
pending_testimonial = Testimonial.objects.pending().first()
if pending_testimonial:
    pending_testimonial.approve(user=request.user)

# Reject a testimonial
testimonial_to_reject = Testimonial.objects.get(id=123)
testimonial_to_reject.reject(reason="Contains inappropriate content", user=request.user)

# Feature a testimonial
testimonial_to_feature = Testimonial.objects.get(id=456)
testimonial_to_feature.feature(user=request.user)

# Add a response to a testimonial
testimonial = Testimonial.objects.get(id=789)
testimonial.add_response(
    "Thank you for your feedback! We're glad our product helped you.",
    user=request.user
)

# Add media to a testimonial
from django.core.files.uploadedfile import SimpleUploadedFile

image = SimpleUploadedFile(
    name='customer_photo.jpg',
    content=open('path/to/image.jpg', 'rb').read(),
    content_type='image/jpeg'
)

testimonial.add_media(
    file_obj=image,
    title="Customer Photo",
    description="Photo provided by the customer"
)

# Get statistics on testimonials
stats = Testimonial.objects.get_stats()
print(f"Total testimonials: {stats['total']}")
print(f"Average rating: {stats['average_rating']}")
print(f"Featured testimonials: {stats['total_featured']}")
```

### Working with Categories

```python
from testimonials.models import TestimonialCategory

# Get all active categories
active_categories = TestimonialCategory.objects.active()

# Get categories with testimonial counts
categories = TestimonialCategory.objects.with_testimonials_count()
for category in categories:
    print(f"{category.name}: {category.testimonials_count} testimonials")
```

### Working with Media

```python
from testimonials.models import TestimonialMedia, Testimonial

# Get all media for a testimonial
testimonial = Testimonial.objects.get(id=123)
media_items = testimonial.media.all()

# Get only images
image_media = testimonial.media.filter(media_type='image')

# Get media by type using the manager
from testimonials.constants import TestimonialMediaType

# Get all image media
images = TestimonialMedia.objects.images()

# Get all video media
videos = TestimonialMedia.objects.videos()

# Set a media item as primary
media_item = testimonial.media.first()
media_item.is_primary = True
media_item.save()  # This will automatically unset is_primary on other media items
```

## Using Forms

Django Testimonials provides forms for collecting and managing testimonials:

### Collecting Testimonials

```python
from testimonials.forms import PublicTestimonialForm
from django.views.generic.edit import FormView
from django.urls import reverse_lazy

class TestimonialSubmissionView(FormView):
    template_name = 'testimonials/submit.html'
    form_class = PublicTestimonialForm
    success_url = reverse_lazy('testimonial_thank_you')
    
    def form_valid(self, form):
        # Associate the testimonial with the current user if authenticated
        if self.request.user.is_authenticated:
            form.instance.author = self.request.user
        
        # Save the testimonial
        form.save()
        return super().form_valid(form)
```

### Admin Management

```python
from testimonials.forms import TestimonialAdminForm
from django.views.generic.edit import UpdateView
from testimonials.models import Testimonial

class TestimonialAdminEditView(UpdateView):
    model = Testimonial
    form_class = TestimonialAdminForm
    template_name = 'testimonials/admin_edit.html'
    success_url = reverse_lazy('testimonial_admin_list')
    
    def form_valid(self, form):
        # Log the action
        action = 'updated'
        if form.instance.status != form.initial.get('status'):
            action = f"changed status to {form.instance.get_status_display()}"
        
        # Your custom logging here
        
        return super().form_valid(form)
```

## Using the REST API

Django Testimonials provides a comprehensive REST API:

### Example API Endpoints

- List testimonials: `GET /testimonials/api/testimonials/`
- Create testimonial: `POST /testimonials/api/testimonials/`
- Get testimonial details: `GET /testimonials/api/testimonials/{id}/`
- Update testimonial: `PUT /testimonials/api/testimonials/{id}/`
- List categories: `GET /testimonials/api/categories/`
- List testimonials for a category: `GET /testimonials/api/categories/{id}/testimonials/`
- List media: `GET /testimonials/api/media/`
- Get media by testimonial: `GET /testimonials/api/media/by-testimonial/?testimonial_id={id}`

### Python Client Example

```python
import requests

# Get published testimonials
response = requests.get('https://yourdomain.com/testimonials/api/testimonials/')
testimonials = response.json()

# Create a new testimonial
data = {
    'author_name': 'API User',
    'content': 'Submitting this testimonial via the API!',
    'rating': 5,
    'category_id': 1
}
response = requests.post(
    'https://yourdomain.com/testimonials/api/testimonials/',
    json=data
)
new_testimonial = response.json()

# Admin: Approve a testimonial
admin_headers = {'Authorization': f'Token {admin_token}'}
response = requests.post(
    f'https://yourdomain.com/testimonials/api/testimonials/{testimonial_id}/approve/',
    headers=admin_headers
)

# Admin: Bulk moderate testimonials
bulk_data = {
    'action': 'approve',
    'testimonial_ids': [123, 456, 789]
}
response = requests.post(
    'https://yourdomain.com/testimonials/api/testimonials/moderate/',
    json=bulk_data,
    headers=admin_headers
)
```

### JavaScript Client Example

```javascript
// Get published testimonials
fetch('/testimonials/api/testimonials/')
  .then(response => response.json())
  .then(data => {
    // Process the testimonials
    data.results.forEach(testimonial => {
      console.log(`${testimonial.author_name}: ${testimonial.content}`);
    });
  });

// Submit a new testimonial
const testimonialData = {
  author_name: 'JS Client User',
  content: 'Submitting via JavaScript client!',
  rating: 5,
  category_id: 1
};

fetch('/testimonials/api/testimonials/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken // Get this from your cookie or context
  },
  body: JSON.stringify(testimonialData)
})
.then(response => response.json())
.then(data => {
  console.log('Testimonial created:', data);
});
```

## Displaying Testimonials

### Django Template Example

```html
{% load static %}

<div class="testimonials-section">
  <h2>What Our Customers Say</h2>
  
  {% for testimonial in testimonials %}
    <div class="testimonial">
      <div class="rating">
        {% for i in "12345"|make_list %}
          {% if forloop.counter <= testimonial.rating %}
            <span class="star filled">★</span>
          {% else %}
            <span class="star">☆</span>
          {% endif %}
        {% endfor %}
      </div>
      
      <blockquote>{{ testimonial.content }}</blockquote>
      
      <div class="author">
        {% if testimonial.avatar %}
          <img src="{{ testimonial.avatar.url }}" alt="{{ testimonial.author_name }}">
        {% endif %}
        <cite>
          {{ testimonial.author_name }}
          {% if testimonial.company %}
            <span class="company">{{ testimonial.company }}</span>
          {% endif %}
        </cite>
      </div>
      
      {% if testimonial.response %}
        <div class="response">
          <p><strong>Our Response:</strong> {{ testimonial.response }}</p>
        </div>
      {% endif %}
      
      {% if testimonial.media.exists %}
        <div class="media-gallery">
          {% for media in testimonial.media.all %}
            {% if media.media_type == 'image' %}
              <img src="{{ media.file.url }}" alt="{{ media.title }}">
            {% elif media.media_type == 'video' %}
              <video controls>
                <source src="{{ media.file.url }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            {% endif %}
          {% endfor %}
        </div>
      {% endif %}
    </div>
  {% endfor %}
</div>
```

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TestimonialSlider = () => {
  const [testimonials, setTestimonials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  
  useEffect(() => {
    // Fetch testimonials from the API
    axios.get('/testimonials/api/testimonials/')
      .then(response => {
        setTestimonials(response.data.results);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching testimonials:', error);
        setLoading(false);
      });
  }, []);
  
  const nextTestimonial = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === testimonials.length - 1 ? 0 : prevIndex + 1
    );
  };
  
  const prevTestimonial = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === 0 ? testimonials.length - 1 : prevIndex - 1
    );
  };
  
  if (loading) {
    return <div>Loading testimonials...</div>;
  }
  
  if (testimonials.length === 0) {
    return <div>No testimonials available.</div>;
  }
  
  const testimonial = testimonials[currentIndex];
  
  return (
    <div className="testimonial-slider">
      <div className="testimonial-content">
        <div className="rating">
          {[1, 2, 3, 4, 5].map(star => (
            <span key={star} className={star <= testimonial.rating ? 'star filled' : 'star'}>
              {star <= testimonial.rating ? '★' : '☆'}
            </span>
          ))}
        </div>
        
        <blockquote>{testimonial.content}</blockquote>
        
        <div className="author">
          {testimonial.avatar && (
            <img src={testimonial.avatar} alt={testimonial.author_name} />
          )}
          <cite>
            {testimonial.author_name}
            {testimonial.company && (
              <span className="company">{testimonial.company}</span>
            )}
          </cite>
        </div>
        
        {testimonial.response && (
          <div className="response">
            <p><strong>Our Response:</strong> {testimonial.response}</p>
          </div>
        )}
      </div>
      
      <div className="navigation">
        <button onClick={prevTestimonial}>&lt; Previous</button>
        <button onClick={nextTestimonial}>Next &gt;</button>
      </div>
    </div>
  );
};

export default TestimonialSlider;
```

## Working with Signals

Django Testimonials provides signals that you can connect to for custom actions:

```python
from django.dispatch import receiver
from testimonials.signals import (
    testimonial_created,
    testimonial_approved,
    testimonial_rejected,
    testimonial_featured,
    testimonial_responded
)

@receiver(testimonial_created)
def handle_new_testimonial(sender, instance, **kwargs):
    """Do something when a new testimonial is created."""
    # For example, send a Slack notification
    send_slack_notification(f"New testimonial from {instance.author_name}")

@receiver(testimonial_approved)
def handle_testimonial_approval(sender, instance, **kwargs):
    """Do something when a testimonial is approved."""
    # For example, update your cache or send a thank-you email
    if instance.author_email:
        send_thank_you_email(instance.author_email)

@receiver(testimonial_rejected)
def handle_testimonial_rejection(sender, instance, reason, **kwargs):
    """Do something when a testimonial is rejected."""
    # For example, log the rejection reason
    logger.info(f"Testimonial {instance.id} rejected: {reason}")

@receiver(testimonial_responded)
def handle_testimonial_response(sender, instance, response, **kwargs):
    """Do something when a response is added to a testimonial."""
    # For example, notify the author about the response
    if instance.author_email:
        send_response_notification(
            instance.author_email,
            instance.content,
            response
        )
```

## Next Steps

- Check out the [API documentation](api.md) for complete details on the REST API
- Learn about [customization options](customization.md) to tailor the package to your needs