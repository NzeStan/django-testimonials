# Django Testimonials

Django Testimonials is a comprehensive, reusable Django package for managing customer testimonials, reviews, and feedback in your web application. Built with flexibility and extensibility in mind, it provides a complete solution for collecting, moderating, and displaying testimonials.

## Features

- **Complete Testimonial Management**: Create, read, update, delete, and moderate testimonials
- **Flexible Data Model**: Support for authors, ratings, categories, and media attachments
- **Moderation Workflow**: Built-in approval, rejection, featuring, and archiving capabilities
- **Media Support**: Attach images, videos, audio, or documents to testimonials
- **Response Management**: Respond to testimonials with official company replies
- **REST API**: Complete Django REST Framework integration
- **UUID Support**: Option to use UUIDs instead of sequential IDs for better security and scalability
- **Internationalization**: All user-facing strings use `gettext_lazy` for easy translation
- **Customizable Admin**: Rich, feature-filled admin interface
- **Signal System**: Comprehensive signals for integrating with other systems
- **Templating System**: Easy-to-use templates for displaying testimonials
- **Extensive Documentation**: Complete documentation and usage examples

## Components

Django Testimonials consists of:

- **Models**: Flexible data models for testimonials, categories, and media
- **Forms**: Ready-to-use forms for testimonial submission and management
- **Admin Interface**: Customized admin interface for easy moderation
- **API**: REST API for integration with JavaScript frontends or mobile apps
- **Templates**: Customizable templates for displaying testimonials
- **Signals**: Comprehensive signal system for extending functionality
- **Utils**: Helper functions and utilities

## Getting Started

1. [Installation Guide](installation.md)
2. [Configuration Options](configuration.md)
3. [Usage Guide](usage.md)
4. [API Documentation](api.md)
5. [Customization Guide](customization.md)
6. [Signals Documentation](signals.md)
7. [Admin](admin.md)

## Example Usage

```python
# Working with testimonials in your views
from testimonials.models import Testimonial

def homepage(request):
    # Get featured testimonials
    featured_testimonials = Testimonial.objects.featured()[:3]
    
    # Get high-rated testimonials (4+ stars)
    high_rated = Testimonial.objects.with_rating(min_rating=4)[:5]
    
    # Get testimonials with media
    testimonials_with_media = Testimonial.objects.filter(media__isnull=False).distinct()
    
    return render(request, 'homepage.html', {
        'featured_testimonials': featured_testimonials,
        'high_rated_testimonials': high_rated,
        'testimonials_with_media': testimonials_with_media
    })
```

```javascript
// Using the API in JavaScript
// Fetch testimonials from the API
fetch('/testimonials/api/testimonials/')
  .then(response => response.json())
  .then(data => {
    // Display testimonials on the page
    const testimonialContainer = document.getElementById('testimonials');
    
    data.results.forEach(testimonial => {
      const testimonialEl = document.createElement('div');
      testimonialEl.className = 'testimonial-card';
      
      // Create rating stars
      const ratingStars = '★'.repeat(testimonial.rating) + 
                         '☆'.repeat(5 - testimonial.rating);
      
      testimonialEl.innerHTML = `
        <div class="testimonial-rating">${ratingStars}</div>
        <blockquote>${testimonial.content}</blockquote>
        <cite>
          <span class="author">${testimonial.author_name}</span>
          ${testimonial.company ? `<span class="company">${testimonial.company}</span>` : ''}
        </cite>
      `;
      
      testimonialContainer.appendChild(testimonialEl);
    });
  });
```

```html
<!-- In your Django template -->
{% load static %}

<div class="testimonials-slider">
  <h2>What Our Customers Say</h2>
  
  <div class="testimonials-container">
    {% for testimonial in featured_testimonials %}
      <div class="testimonial-card {% if testimonial.status == 'featured' %}featured{% endif %}">
        <div class="testimonial-rating">
          {% for i in "12345"|make_list %}
            {% if forloop.counter <= testimonial.rating %}
              <span class="star filled">★</span>
            {% else %}
              <span class="star">☆</span>
            {% endif %}
          {% endfor %}
        </div>
        
        <blockquote>{{ testimonial.content }}</blockquote>
        
        <cite>
          {% if testimonial.avatar %}
            <img src="{{ testimonial.avatar.url }}" alt="{{ testimonial.author_name }}" class="avatar">
          {% endif %}
          <span class="author">{{ testimonial.author_name }}</span>
          {% if testimonial.company %}
            <span class="company">{{ testimonial.company }}</span>
          {% endif %}
        </cite>
        
        {% if testimonial.response %}
          <div class="testimonial-response">
            <h4>Our Response:</h4>
            <p>{{ testimonial.response }}</p>
          </div>
        {% endif %}
      </div>
    {% empty %}
      <p>No testimonials available.</p>
    {% endfor %}
  </div>
</div>
```

## Testimonial Submission Form

Django Testimonials makes it easy to collect testimonials from your users:

```python
# In your views.py
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from testimonials.forms import PublicTestimonialForm

class SubmitTestimonialView(FormView):
    template_name = 'submit_testimonial.html'
    form_class = PublicTestimonialForm
    success_url = reverse_lazy('testimonial_thank_you')
    
    def form_valid(self, form):
        # Set the current user as the author if authenticated
        if self.request.user.is_authenticated:
            form.instance.author = self.request.user
        
        # Save the testimonial
        form.save()
        return super().form_valid(form)
```

```html
<!-- In your template -->
<div class="testimonial-form-container">
  <h2>Share Your Experience</h2>
  
  <form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    
    {{ form.non_field_errors }}
    
    <div class="form-group">
      <label for="{{ form.author_name.id_for_label }}">Your Name</label>
      {{ form.author_name }}
      {{ form.author_name.errors }}
    </div>
    
    <div class="form-group">
      <label for="{{ form.email.id_for_label }}">Email (optional)</label>
      {{ form.author_email }}
      {{ form.author_email.errors }}
      <small>Your email will not be displayed publicly.</small>
    </div>
    
    <div class="form-group">
      <label for="{{ form.company.id_for_label }}">Company (optional)</label>
      {{ form.company }}
      {{ form.company.errors }}
    </div>
    
    <div class="form-group">
      <label>Rating</label>
      {{ form.rating }}
      {{ form.rating.errors }}
    </div>
    
    <div class="form-group">
      <label for="{{ form.content.id_for_label }}">Your Testimonial</label>
      {{ form.content }}
      {{ form.content.errors }}
    </div>
    
    {% if form.category %}
    <div class="form-group">
      <label for="{{ form.category.id_for_label }}">Category (optional)</label>
      {{ form.category }}
      {{ form.category.errors }}
    </div>
    {% endif %}
    
    <div class="form-group">
      <label for="{{ form.avatar.id_for_label }}">Your Photo (optional)</label>
      {{ form.avatar }}
      {{ form.avatar.errors }}
    </div>
    
    <div class="form-check">
      {{ form.is_anonymous }}
      <label for="{{ form.is_anonymous.id_for_label }}" class="form-check-label">
        Submit anonymously
      </label>
      {{ form.is_anonymous.errors }}
    </div>
    
    <button type="submit" class="btn btn-primary">Submit Testimonial</button>
  </form>
</div>
```

## Admin Interface

Django Testimonials provides a rich admin interface for managing testimonials:

![Admin Interface Preview](https://example.com/path/to/admin-screenshot.png) ##attend to this

Key features of the admin interface:
- Filter testimonials by status, rating, category, and more
- Quick action buttons for approving, rejecting, featuring, and archiving testimonials
- Visual rating display with stars
- Media management with image previews
- Bulk moderation actions
- Enhanced detail view with all testimonial information

## API Endpoints

The API provides all the functionality needed to integrate testimonials into your frontend application:

- `GET /testimonials/api/testimonials/` - List all testimonials
- `POST /testimonials/api/testimonials/` - Create a new testimonial
- `GET /testimonials/api/testimonials/{id}/` - Get a specific testimonial
- `PATCH /testimonials/api/testimonials/{id}/` - Update a testimonial
- `DELETE /testimonials/api/testimonials/{id}/` - Delete a testimonial
- `POST /testimonials/api/testimonials/{id}/approve/` - Approve a testimonial
- `POST /testimonials/api/testimonials/{id}/reject/` - Reject a testimonial
- `POST /testimonials/api/testimonials/{id}/respond/` - Add a response to a testimonial
- `GET /testimonials/api/categories/` - List testimonial categories
- `GET /testimonials/api/media/` - List testimonial media
- `POST /testimonials/api/testimonials/{id}/add_media/` - Add media to a testimonial

## Customization

Django Testimonials is designed to be customized to fit your specific needs. You can:

- Extend the base models to add additional fields
- Create custom forms with additional validation
- Customize the admin interface
- Override templates to match your site's design
- Connect to signals to integrate with other systems
- Create custom model managers for specialized queries

See the [Customization Guide](customization.md) for details.

## Requirements

- Python 3.8+
- Django 3.2+
- Django REST Framework 3.12+
- Pillow (for image handling)
- django-phonenumber-field with phonenumbers support
- django-filter 2.4.0+


## License

Django Testimonials is released under the MIT License. See the [LICENSE](https://github.com/NzeStan/django-testimonials/blob/main/LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you have any questions or need help with implementation, please open an issue on the [GitHub repository](https://github.com/NzeStan/django-testimonials/issues).