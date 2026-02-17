# Production Deployment Guide

This guide covers enterprise-grade deployment strategies for Django Testimonials in production environments, including containerization, cloud deployment, and monitoring.

## Deployment Architecture

### Recommended Production Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     CDN         │    │   Monitoring    │
│  (nginx/HAProxy)│    │  (CloudFront)   │    │   (Grafana)     │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Servers   │    │   Static Files  │    │   Log Storage   │
│   (Gunicorn)    │◄──►│   (S3/GCS)      │    │   (ELK Stack)   │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   Background    │    │   File Storage  │
│   (Django)      │◄──►│   (Threads)     │    │   (S3/GCS)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   Cache         │
│   (PostgreSQL)  │    │   (Database)    │
└─────────────────┘    └─────────────────┘
```

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "your_project.wsgi:application"]
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:password@db:5432/testimonials
    depends_on:
      - db
    volumes:
      - media_volume:/app/media
      - static_volume:/app/staticfiles
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  background-tasks:
    build: .
    command: python manage.py process_tasks
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:password@db:5432/testimonials
    depends_on:
      - db
    volumes:
      - media_volume:/app/media
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=testimonials
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - media_volume:/var/www/media
      - static_volume:/var/www/static
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  media_volume:
  static_volume:
```

### Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript
               application/xml+rss application/atom+xml image/svg+xml;

    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=1r/s;

    upstream django {
        server web:8000;
    }

    server {
        listen 80;
        server_name your-domain.com www.your-domain.com;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com www.your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;

        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /var/www/media/;
            expires 1M;
            add_header Cache-Control "public";
        }

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            limit_req zone=general burst=5 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health/ {
            proxy_pass http://django;
            access_log off;
        }
    }
}
```

## Environment Configuration

### Using django-environ

```python
# settings/production.py
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_CACHE=(bool, True),
    USE_BACKGROUND_TASKS=(bool, True),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

DATABASES = {
    'default': env.db()
}

# Cache
if env('USE_CACHE'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'testimonials_cache_table',
        }
    }

# File storage - use your preferred backend
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Testimonials settings
TESTIMONIALS_USE_CACHE = env('USE_CACHE')
TESTIMONIALS_USE_BACKGROUND_TASKS = env('USE_BACKGROUND_TASKS')
TESTIMONIALS_NOTIFICATION_EMAIL = env('TESTIMONIALS_NOTIFICATION_EMAIL', default=None)
```

### .env Template

```bash
# .env.template

# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/testimonials

# Cache
USE_CACHE=True

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Your Site <noreply@yoursite.com>

# Testimonials
TESTIMONIALS_NOTIFICATION_EMAIL=admin@yoursite.com
TESTIMONIALS_MAX_FILE_SIZE=10485760
TESTIMONIALS_CACHE_TIMEOUT=900

# Performance
USE_BACKGROUND_TASKS=True

# Monitoring
SENTRY_DSN=your-sentry-dsn
```

## Monitoring & Logging

### Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/testimonials.log',
            'maxBytes': 1024*1024*5,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'testimonials': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Health Check Endpoint

```python
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.utils import timezone

@never_cache
@require_http_methods(["GET"])
def health_check(request):
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = {'status': 'healthy'}
    except Exception as e:
        health_status['checks']['database'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'

    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['checks']['cache'] = {'status': 'healthy'}
        else:
            health_status['checks']['cache'] = {'status': 'unhealthy'}
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['cache'] = {'status': 'unhealthy', 'error': str(e)}

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
```

## Security Configuration

### Production Security Settings

```python
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

## Media & File Storage

Django Testimonials uses standard Django `FileField` and `ImageField`, so it works with **any** Django storage backend. Configure your preferred storage in `settings.py`:

### Local Storage (Default)
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

### AWS S3
```python
# pip install django-storages boto3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
AWS_S3_REGION_NAME = 'us-west-2'
```

### Cloudinary
```python
# pip install django-cloudinary-storage cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'your-cloud-name',
    'API_KEY': 'your-api-key',
    'API_SECRET': 'your-api-secret',
}
```

### Google Cloud Storage
```python
# pip install django-storages google-cloud-storage
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
GS_BUCKET_NAME = 'your-bucket-name'
GS_PROJECT_ID = 'your-project-id'
```

### Azure Blob Storage
```python
# pip install django-storages azure-storage-blob
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = 'your-account-name'
AZURE_ACCOUNT_KEY = 'your-account-key'
AZURE_CONTAINER = 'media'
```

## CI/CD with GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_testimonials
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -e .[dev]
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_testimonials
      run: pytest --cov=testimonials --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4
    - name: Deploy
      run: echo "Add your deployment steps here"
```

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Security settings enabled (HTTPS, HSTS, secure cookies)
- [ ] `DEBUG = False`
- [ ] `ALLOWED_HOSTS` configured
- [ ] Secret key is unique and not in version control

### Application
- [ ] `django-testimonials` installed and in `INSTALLED_APPS`
- [ ] `TESTIMONIALS_USE_CACHE = True` for production
- [ ] Cache backend configured and cache table created
- [ ] File storage backend configured (S3, Cloudinary, etc.)
- [ ] Email backend configured for notifications
- [ ] Background tasks enabled if needed

### Infrastructure
- [ ] Database provisioned and accessible
- [ ] Load balancer / reverse proxy configured
- [ ] SSL certificates installed
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up
- [ ] Backup strategy implemented
- [ ] Health check endpoint accessible
