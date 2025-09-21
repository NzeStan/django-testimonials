# Performance Optimization Guide

This guide covers advanced performance optimization strategies for Django Testimonials, helping you achieve enterprise-grade performance at scale.

## 🎯 **Performance Targets**

| Metric | Target | Enterprise Target |
|--------|--------|------------------|
| API Response Time | <100ms | <50ms |
| Database Query Time | <10ms | <5ms |
| Cache Hit Rate | >90% | >95% |
| Concurrent Users | 1,000+ | 10,000+ |
| Testimonials Handled | 100K+ | 1M+ |

## 📊 **Performance Monitoring**

### **Built-in Performance Monitoring**

Django Testimonials includes built-in performance monitoring:

```python
# Enable performance monitoring
TESTIMONIALS_ENABLE_PERFORMANCE_MONITORING = True

# Configure performance thresholds
TESTIMONIALS_SLOW_QUERY_THRESHOLD = 10  # milliseconds
TESTIMONIALS_SLOW_API_THRESHOLD = 100  # milliseconds
```

### **Django Debug Toolbar (Development)**

```bash
pip install django-debug-toolbar
```

```python
# settings.py (development only)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }
```

### **Production Monitoring**

#### **Sentry Integration**
```bash
pip install sentry-sdk[django]
```

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[
        DjangoIntegration(
            transaction_style='url',
            middleware_spans=True,
            signals_spans=True,
        ),
        CeleryIntegration(monitor_beat_tasks=True),
        RedisIntegration(),
    ],
    traces_sample_rate=0.1,  # Adjust based on traffic
    send_default_pii=True,
)
```

#### **New Relic Integration**
```bash
pip install newrelic
```

```python
# Add to your WSGI application
import newrelic.agent
application = newrelic.agent.WSGIApplicationWrapper(application)
```

## 🚄 **Database Optimization**

### **PostgreSQL Optimization**

#### **Database Settings**
```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

#### **Index Optimization**
```sql
-- Create additional indexes for heavy queries
CREATE INDEX CONCURRENTLY testimonial_status_created_idx 
ON testimonials_testimonial(status, created_at);

CREATE INDEX CONCURRENTLY testimonial_rating_status_idx 
ON testimonials_testimonial(rating, status) 
WHERE status IN ('approved', 'featured');

CREATE INDEX CONCURRENTLY testimonial_author_status_idx 
ON testimonials_testimonial(author_id, status);

-- Full-text search index
CREATE INDEX CONCURRENTLY testimonial_content_gin_idx 
ON testimonials_testimonial 
USING gin(to_tsvector('english', content));

-- Partial index for published testimonials
CREATE INDEX CONCURRENTLY testimonial_published_idx 
ON testimonials_testimonial(created_at DESC) 
WHERE status IN ('approved', 'featured');
```

#### **Query Optimization**
```python
# Use database functions for better performance
from django.contrib.postgres.search import SearchVector, SearchQuery
from django.db.models import F, Q

# Optimized search using PostgreSQL full-text search
testimonials = Testimonial.objects.annotate(
    search=SearchVector('content', 'author_name', 'company')
).filter(search=SearchQuery('django awesome'))

# Use database aggregation instead of Python loops
stats = Testimonial.objects.aggregate(
    avg_rating=Avg('rating'),
    total_count=Count('id'),
    high_rated_count=Count('id', filter=Q(rating__gte=4))
)
```

### **MySQL Optimization**

#### **Database Settings**
```sql
-- my.cnf optimizations
innodb_buffer_pool_size = 256M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2
query_cache_size = 64M
query_cache_type = 1
```

#### **Index Optimization**
```sql
-- Composite indexes for common queries
ALTER TABLE testimonials_testimonial 
ADD INDEX idx_status_created (status, created_at);

ALTER TABLE testimonials_testimonial 
ADD INDEX idx_rating_status (rating, status);

-- Full-text search index
ALTER TABLE testimonials_testimonial 
ADD FULLTEXT(content, author_name, company);
```

### **Connection Pooling**

#### **Django Database Pooling**
```bash
pip install django-db-pool
```

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django_db_pool.backends.postgresql',
        'NAME': 'your_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    }
}
```

#### **PgBouncer (PostgreSQL)**
```bash
# Install PgBouncer
sudo apt-get install pgbouncer

# Configure /etc/pgbouncer/pgbouncer.ini
[databases]
your_db = host=localhost port=5432 dbname=your_db

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
```

## ⚡ **Redis Cache Optimization**

### **Redis Configuration**

#### **redis.conf Optimization**
```bash
# Memory optimization
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence (adjust based on needs)
save 900 1
save 300 10
save 60 10000

# Network optimization
tcp-keepalive 300
timeout 0
```

#### **Advanced Redis Settings**
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
                'socket_keepalive': True,
                'socket_keepalive_options': {},
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'testimonials',
        'VERSION': 1,
        'TIMEOUT': 900,  # 15 minutes
    }
}
```

### **Cache Strategies**

#### **Cache Warming**
```python
# Management command: warm_testimonial_cache.py
from django.core.management.base import BaseCommand
from testimonials.models import Testimonial, TestimonialCategory

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Warm featured testimonials cache
        Testimonial.objects.featured()
        
        # Warm category cache
        TestimonialCategory.objects.active()
        
        # Warm statistics cache
        Testimonial.objects.get_stats()
        
        self.stdout.write('Cache warmed successfully')
```

#### **Cache Invalidation Strategy**
```python
# Custom cache invalidation
from django.core.cache import cache
from testimonials.utils import get_cache_key

def invalidate_testimonial_caches(testimonial_id, category_id=None):
    """Intelligent cache invalidation."""
    keys_to_invalidate = [
        get_cache_key('testimonial', testimonial_id),
        get_cache_key('featured_testimonials'),
        get_cache_key('stats'),
    ]
    
    if category_id:
        keys_to_invalidate.extend([
            get_cache_key('category', category_id),
            get_cache_key('category_testimonials', category_id),
        ])
    
    cache.delete_many(keys_to_invalidate)
```

## 🔄 **Celery Optimization**

### **Celery Configuration**

#### **Production Settings**
```python
# celery.py
from celery import Celery
from kombu import Queue, Exchange

app = Celery('testimonials')

# Broker settings
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    
    # Performance settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Queue configuration
    task_routes={
        'testimonials.tasks.send_testimonial_email': {'queue': 'emails'},
        'testimonials.tasks.process_media': {'queue': 'media'},
        'testimonials.tasks.bulk_moderate': {'queue': 'bulk'},
    },
    
    # Queue definitions
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('emails', Exchange('emails'), routing_key='emails'),
        Queue('media', Exchange('media'), routing_key='media'),
        Queue('bulk', Exchange('bulk'), routing_key='bulk'),
    ),
    
    # Retry settings
    task_retry_backoff=True,
    task_retry_backoff_max=700,
    task_retry_jitter=False,
)
```

#### **Worker Optimization**
```bash
# Start optimized workers
celery -A testimonials worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --queue=default,emails

# Start specialized workers
celery -A testimonials worker \
    --loglevel=info \
    --concurrency=2 \
    --queue=media \
    --hostname=media@%h

celery -A testimonials worker \
    --loglevel=info \
    --concurrency=1 \
    --queue=bulk \
    --hostname=bulk@%h
```

### **Task Optimization**

#### **Batch Processing**
```python
# Optimized bulk email task
from celery import group
from testimonials.tasks import send_testimonial_email

def send_bulk_emails(testimonial_ids, email_type):
    """Send emails in batches for better performance."""
    batch_size = 50
    
    for i in range(0, len(testimonial_ids), batch_size):
        batch = testimonial_ids[i:i + batch_size]
        
        # Create group of tasks
        job = group(
            send_testimonial_email.s(tid, email_type)
            for tid in batch
        )
        
        # Execute batch
        job.apply_async()
```

## 🌐 **API Optimization**

### **Response Optimization**

#### **Compression**
```python
# settings.py
MIDDLEWARE += ['django.middleware.gzip.GZipMiddleware']

# Enable compression for API responses
GZIP_CONTENT_TYPES = [
    'application/json',
    'application/javascript',
    'text/css',
    'text/html',
    'text/javascript',
    'text/plain',
    'text/xml',
]
```

#### **HTTP Caching Headers**
```python
# In your API views
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator

@method_decorator(cache_control(max_age=300), name='list')  # 5 minutes
class TestimonialViewSet(viewsets.ModelViewSet):
    # ... your viewset code
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # Add ETag for client-side caching
        response['ETag'] = f'"{hash(str(response.data))}"'
        
        return response
```

### **Pagination Optimization**

#### **Cursor Pagination**
```python
from rest_framework.pagination import CursorPagination

class TestimonialCursorPagination(CursorPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    ordering = '-created_at'  # Must be unique, ordered field

class TestimonialViewSet(viewsets.ModelViewSet):
    pagination_class = TestimonialCursorPagination
```

### **Query Optimization**

#### **Select Related Optimization**
```python
# Optimized queryset in viewsets
def get_queryset(self):
    return Testimonial.objects.select_related(
        'category',
        'author',
        'approved_by'
    ).prefetch_related(
        Prefetch(
            'media',
            queryset=TestimonialMedia.objects.select_related().order_by(
                '-is_primary', 'order'
            )
        )
    ).only(
        'id', 'author_name', 'content', 'rating', 'status',
        'created_at', 'category__name', 'author__username'
    )
```

## 📁 **File Upload Optimization**

### **Media Storage Optimization**

#### **AWS S3 Configuration**
```bash
pip install django-storages boto3
```

```python
# settings.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
AWS_S3_REGION_NAME = 'us-west-2'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'

# CloudFront CDN
AWS_S3_CUSTOM_DOMAIN = 'your-cdn-domain.cloudfront.net'
```

#### **Thumbnail Generation Optimization**
```python
# Optimized thumbnail settings
TESTIMONIALS_THUMBNAIL_SIZES = {
    'small': (150, 150),
    'medium': (300, 300),
    'large': (600, 600),
}

# Use WebP format for better compression
TESTIMONIALS_THUMBNAIL_FORMAT = 'WEBP'
TESTIMONIALS_THUMBNAIL_QUALITY = 85
```

### **File Validation**

#### **Optimized File Validation**
```python
# Custom file validator
from django.core.exceptions import ValidationError
from PIL import Image
import magic

def validate_image_file(file):
    """Optimized image validation."""
    # Check file type using python-magic
    mime_type = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)
    
    if mime_type not in ['image/jpeg', 'image/png', 'image/webp']:
        raise ValidationError('Invalid image format')
    
    # Validate image using Pillow
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except Exception:
        raise ValidationError('Invalid image file')
    
    # Check dimensions
    if img.width > 4096 or img.height > 4096:
        raise ValidationError('Image too large')
```

## 🔍 **Search Optimization**

### **PostgreSQL Full-Text Search**

```python
# Add search vector field
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class Testimonial(models.Model):
    # ... existing fields
    search_vector = SearchVectorField(null=True, blank=True)
    
    class Meta:
        indexes = [
            GinIndex(fields=['search_vector']),
            # ... other indexes
        ]
```

```python
# Update search vector
from django.contrib.postgres.search import SearchVector

def update_search_vector():
    """Update search vectors for all testimonials."""
    Testimonial.objects.update(
        search_vector=SearchVector(
            'content', weight='A',
            'author_name', weight='B',
            'company', weight='C',
        )
    )
```

### **Elasticsearch Integration**

```bash
pip install django-elasticsearch-dsl
```

```python
# documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from testimonials.models import Testimonial

@registry.register_document
class TestimonialDocument(Document):
    category = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(),
    })
    
    class Index:
        name = 'testimonials'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }
    
    class Django:
        model = Testimonial
        fields = [
            'id',
            'author_name',
            'content',
            'rating',
            'created_at',
        ]
```

## 📈 **Performance Monitoring & Alerts**

### **Custom Performance Metrics**

```python
# Custom middleware for performance monitoring
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('performance')

class PerformanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests
            if duration > 0.5:  # 500ms threshold
                logger.warning(
                    f'Slow request: {request.method} {request.path} '
                    f'took {duration:.2f}s'
                )
            
            # Add response header
            response['X-Response-Time'] = f'{duration:.3f}'
        
        return response
```

### **Health Check Endpoints**

```python
# health.py
from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection
import redis

def health_check(request):
    """Comprehensive health check."""
    status = {
        'database': False,
        'cache': False,
        'celery': False,
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['database'] = True
    except Exception:
        pass
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        status['cache'] = cache.get('health_check') == 'ok'
    except Exception:
        pass
    
    # Celery check
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        status['celery'] = bool(stats)
    except Exception:
        pass
    
    overall_status = all(status.values())
    
    return JsonResponse({
        'status': 'healthy' if overall_status else 'unhealthy',
        'components': status
    }, status=200 if overall_status else 503)
```

## 📊 **Performance Benchmarking**

### **Load Testing with Locust**

```bash
pip install locust
```

```python
# locustfile.py
from locust import HttpUser, task, between
import random

class TestimonialUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login if required
        pass
    
    @task(3)
    def list_testimonials(self):
        self.client.get("/api/testimonials/")
    
    @task(2)
    def get_testimonial_detail(self):
        testimonial_id = random.randint(1, 100)
        self.client.get(f"/api/testimonials/{testimonial_id}/")
    
    @task(1)
    def create_testimonial(self):
        self.client.post("/api/testimonials/", json={
            "author_name": f"User {random.randint(1, 1000)}",
            "content": "Great product! " * random.randint(5, 20),
            "rating": random.randint(4, 5)
        })
    
    @task(1)
    def search_testimonials(self):
        search_terms = ["great", "awesome", "excellent", "amazing"]
        term = random.choice(search_terms)
        self.client.get(f"/api/testimonials/?search={term}")
```

```bash
# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### **Database Query Analysis**

```python
# Management command: analyze_queries.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import override_settings

class Command(BaseCommand):
    @override_settings(DEBUG=True)
    def handle(self, *args, **options):
        # Reset query log
        connection.queries_log.clear()
        
        # Run your operations
        from testimonials.models import Testimonial
        testimonials = Testimonial.objects.published()[:10]
        
        # Analyze queries
        self.stdout.write(f"Total queries: {len(connection.queries)}")
        
        for query in connection.queries:
            self.stdout.write(f"Time: {query['time']}s")
            self.stdout.write(f"SQL: {query['sql']}")
            self.stdout.write("-" * 50)
```

## 🚀 **Performance Checklist**

### **Database**
- [ ] Proper indexes on all filtered/ordered fields
- [ ] Composite indexes for complex queries
- [ ] Connection pooling configured
- [ ] Query optimization completed
- [ ] Database settings tuned

### **Caching**
- [ ] Redis installed and configured
- [ ] Cache keys properly namespaced
- [ ] Cache invalidation strategy implemented
- [ ] Cache hit rate monitoring enabled

### **Background Tasks**
- [ ] Celery installed and configured
- [ ] Task queues properly organized
- [ ] Worker processes optimized
- [ ] Task monitoring enabled

### **API**
- [ ] Response compression enabled
- [ ] Proper HTTP caching headers
- [ ] Query optimization with select_related/prefetch_related
- [ ] Pagination implemented

### **Monitoring**
- [ ] Performance monitoring enabled
- [ ] Slow query detection configured
- [ ] Health check endpoints implemented
- [ ] Error tracking configured

**Remember:** Performance optimization is an iterative process. Monitor, measure, and optimize based on your specific usage patterns!