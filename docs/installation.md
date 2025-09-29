# Installation Guide

This comprehensive guide covers installation, setup, and configuration of Django Testimonials for both development and production environments.

## 📋 **Prerequisites**

### **System Requirements**
- **Python:** 3.8+ (3.10+ recommended)
- **Django:** 3.2+ (4.2+ recommended) 
- **Database:** PostgreSQL 12+ (recommended) or MySQL 5.7+
- **Memory:** 512MB minimum (2GB+ recommended for production)

### **Optional Dependencies for Performance**
- **Redis:** 6.0+ for caching and session storage
- **Celery:** 5.0+ for background task processing
- **nginx:** For production deployments

## 🚀 **Installation Methods**

### **Method 1: PyPI (Recommended)**

```bash
# Basic installation
pip install django-testimonials

# With optional performance dependencies
pip install django-testimonials[performance]

# Development installation with testing tools
pip install django-testimonials[dev]
```

### **Method 2: From Source**

```bash
# Clone the repository
git clone https://github.com/NzeStan/django-testimonials.git
cd django-testimonials

# Install in development mode
pip install -e .

# install with optional dependencies
pip install -e .[performance]

# Development installation with testing tools
pip install -e .[dev]
```

### **Method 3: Using Poetry**

```bash
# Add to your project
poetry add django-testimonials

# With optional dependencies
poetry add django-testimonials[performance]

# Development installation with testing tools
poetry add django-testimonials[dev]
```

### **Method 4: Using pipenv**

```bash
# Basic installation
pipenv install django-testimonials

# With optional dependencies
pipenv install django-testimonials[performance]

# Development installation with testing tools
pipenv install django-testimonials[dev]

```

## ⚙️ **Basic Setup**

### **1. Django Settings**

Add the required applications to your `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'phonenumber_field',
    
    # Django Testimonials
    'testimonials',
    
    # Your apps
    'your_app',
]
```

### **2. Database Configuration**

#### **PostgreSQL (Recommended)**
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_database',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'charset': 'utf8',
        },
    }
}
```

#### **MySQL**
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_database',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

#### **SQLite (Development Only)**
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### **3. Run Migrations**

```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate
```

### **4. URL Configuration**

```python
# urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Django Testimonials API
    path('api/testimonials/', include('testimonials.api.urls')),
    
    # Optional: Include main testimonials URLs
    path('testimonials/', include('testimonials.urls')),
    
    # Your app URLs
    path('', include('your_app.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### **5. Media Files Configuration**

```python
# settings.py
import os

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Additional locations of static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
```

### **6. Basic Testimonials Configuration**

```python
# settings.py

# Basic testimonials settings
TESTIMONIALS_REQUIRE_APPROVAL = True
TESTIMONIALS_ALLOW_ANONYMOUS = True
TESTIMONIALS_MAX_RATING = 5
TESTIMONIALS_PAGINATION_SIZE = 10

# Email notifications
TESTIMONIALS_NOTIFICATION_EMAIL = 'admin@yoursite.com'

# File uploads
TESTIMONIALS_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
TESTIMONIALS_ENABLE_MEDIA = True
```

## ⚡ **Performance Setup (Recommended)**

### **Redis Installation & Configuration**

#### **Install Redis**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# CentOS/RHEL
sudo yum install redis

# Start Redis
sudo systemctl start redis
```

#### **Django Redis Configuration**
```python
# settings.py
INSTALLED_APPS += ['django_redis']

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'testimonials',
        'VERSION': 1,
    }
}

# Enable Redis caching for testimonials
TESTIMONIALS_USE_REDIS_CACHE = True
TESTIMONIALS_REDIS_CACHE_URL = 'redis://localhost:6379/1'
TESTIMONIALS_CACHE_TIMEOUT = 900  # 15 minutes
```

### **Celery Installation & Configuration**

#### **Install Celery**
```bash
pip install celery[redis]
```

#### **Celery Configuration**
```python
# settings.py
import os

# Celery configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Enable Celery for testimonials
TESTIMONIALS_USE_CELERY = True
TESTIMONIALS_CELERY_BROKER_URL = 'redis://localhost:6379/0'

# Periodic tasks
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-cache': {
        'task': 'testimonials.tasks.cleanup_expired_cache',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'generate-testimonial-stats': {
        'task': 'testimonials.tasks.generate_testimonial_stats',
        'schedule': crontab(minute=0, hour='*/1'),  # Every hour
    },
    'optimize-database': {
        'task': 'testimonials.tasks.optimize_database',
        'schedule': crontab(minute=0, hour=3),  # Daily at 3 AM
    },
}
```

#### **Create Celery App**
```python
# celery.py (in your project root)
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

#### **Update __init__.py**
```python
# __init__.py (in your project root)
from .celery import app as celery_app

__all__ = ('celery_app',)
```

#### **Start Celery Workers**
```bash
# In separate terminal windows

# Start Celery worker
celery -A your_project worker --loglevel=info

# Start Celery beat scheduler (for periodic tasks)
celery -A your_project beat --loglevel=info

# Optional: Start Celery flower for monitoring
pip install flower
celery -A your_project flower
```

## 📧 **Email Configuration**

### **SMTP Configuration**
```python
# settings.py

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# SMTP settings
EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'Your Site <noreply@yoursite.com>'

# Testimonials email settings
TESTIMONIALS_NOTIFICATION_EMAIL = 'admin@yoursite.com'
TESTIMONIALS_EMAIL_RATE_LIMIT = 60  # emails per minute
```

### **Email Testing (Development)**
```python
# settings.py (for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## 🔐 **Security Configuration**

### **REST Framework Settings**
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

### **CORS Configuration (if using frontend framework)**
```bash
pip install django-cors-headers
```

```python
# settings.py
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... other middleware
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8080",  # Vue dev server
]

# For production, use your actual domain
# CORS_ALLOWED_ORIGINS = ["https://yoursite.com"]
```

## 🧪 **Verification & Testing**

### **1. Create a Superuser**
```bash
python manage.py createsuperuser
```

### **2. Start Development Server**
```bash
python manage.py runserver
```

### **3. Test Basic Functionality**

#### **Admin Interface**
Visit: `http://localhost:8000/admin/`
- Log in with your superuser account
- Navigate to "Testimonials" section
- Create a test category and testimonial

#### **API Endpoints**
Test the API endpoints:

```bash
# List testimonials
curl http://localhost:8000/api/testimonials/

# Create a testimonial
curl -X POST http://localhost:8000/api/testimonials/ \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Test User",
    "content": "Great product!",
    "rating": 5
  }'
```

### **4. Performance Verification**

#### **Check Redis Connection**
```python
# In Django shell: python manage.py shell
from django.core.cache import cache
cache.set('test_key', 'test_value', 30)
print(cache.get('test_key'))  # Should print: test_value
```

#### **Check Celery Connection**
```python
# In Django shell: python manage.py shell
from testimonials.tasks import send_testimonial_notification_email
result = send_testimonial_notification_email.delay('test_id', 'approved', 'test@example.com')
print(f"Task ID: {result.id}")
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Migration Errors**
```bash
# Reset migrations (development only)
python manage.py migrate testimonials zero
python manage.py migrate testimonials

# Or delete migration files and recreate
rm testimonials/migrations/0*.py
python manage.py makemigrations testimonials
python manage.py migrate
```

#### **Redis Connection Issues**
```bash
# Check Redis status
redis-cli ping  # Should return: PONG

# Check Redis logs
sudo journalctl -u redis

# Restart Redis
sudo systemctl restart redis
```

#### **Celery Issues**
```bash
# Check Celery worker status
celery -A your_project status

# Purge all tasks
celery -A your_project purge

# Monitor tasks
celery -A your_project events
```

#### **File Upload Issues**
```python
# Ensure media directories exist
import os
from django.conf import settings

os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_ROOT, 'testimonials'), exist_ok=True)
```

### **Performance Issues**

#### **Slow Queries**
```python
# Enable query logging (development only)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'testimonials': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

#### **Memory Issues**
```python
# Optimize pagination for large datasets
TESTIMONIALS_PAGINATION_SIZE = 25  # Reduce if memory issues
TESTIMONIALS_SEARCH_RESULTS_LIMIT = 500  # Limit search results

# Enable database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes
```

## 🚀 **Production Deployment**

### **Environment Variables**
Create a `.env` file for sensitive settings:

```bash
# .env
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0

# Email settings
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-app-password

# Testimonials settings
TESTIMONIALS_NOTIFICATION_EMAIL=admin@yoursite.com
```

### **Load Environment Variables**
```python
# settings.py
import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Use environment variables
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
DATABASES = {
    'default': env.db()
}
```

### **Static Files for Production**
```bash
# Collect static files
python manage.py collectstatic --noinput
```

### **Security Settings**
```python
# settings.py (production)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# If using HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

## ✅ **Installation Checklist**

### **Basic Setup**
- [ ] Python 3.8+ installed
- [ ] Django 3.2+ installed
- [ ] Django Testimonials installed
- [ ] Added to INSTALLED_APPS
- [ ] Migrations applied
- [ ] URLs configured
- [ ] Media files configured
- [ ] Admin superuser created

### **Performance Setup (Optional)**
- [ ] Redis installed and running
- [ ] Redis cache configured
- [ ] Celery installed
- [ ] Celery workers running
- [ ] Celery beat scheduler running
- [ ] Email backend configured

### **Production Setup**
- [ ] Environment variables configured
- [ ] Static files collected
- [ ] Security settings applied
- [ ] Database optimized
- [ ] Monitoring configured
- [ ] Backup strategy implemented

## 📚 **Next Steps**

1. **[Configuration Guide](configuration.md)** - Explore all configuration options
2. **[Usage Guide](usage.md)** - Learn how to use all features
3. **[API Documentation](api.md)** - Complete API reference
4. **[Performance Guide](performance.md)** - Optimization strategies
5. **[Deployment Guide](deployment.md)** - Production deployment

## 🆘 **Getting Help**

If you encounter issues:

1. **Check the documentation** - Most common issues are covered
2. **Search existing issues** - [GitHub Issues](https://github.com/NzeStan/django-testimonials/issues)
3. **Create a new issue** - Include your configuration and error details
4. **Join discussions** - [GitHub Discussions](https://github.com/NzeStan/django-testimonials/discussions)

**Pro Tip:** Include your Django version, Python version, and relevant configuration when asking for help!