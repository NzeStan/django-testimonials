# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "your_project.wsgi:application"]
```

### **Docker Compose Setup**

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
      - REDIS_URL=redis://redis:6379/1
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - media_volume:/app/media
      - static_volume:/app/staticfiles
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery-worker:
    build: .
    command: celery -A your_project worker --loglevel=info --concurrency=4
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:password@db:5432/testimonials
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - media_volume:/app/media
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A your_project beat --loglevel=info
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:password@db:5432/testimonials
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=testimonials
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
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
  redis_data:
  media_volume:
  static_volume:
```

### **Production Requirements**

```txt
# requirements.txt
Django>=4.2,<5.0
djangorestframework>=3.14.0
django-filter>=23.2
django-phonenumber-field[phonenumbers]>=7.1.0
Pillow>=10.0.0

# Performance & Caching
django-redis>=5.3.0
celery[redis]>=5.3.0
redis>=4.6.0

# Database
psycopg2-binary>=2.9.7
django-db-pool>=1.0.0

# Production
gunicorn>=21.2.0
whitenoise>=6.5.0
django-storages[boto3]>=1.13.2

# Monitoring
sentry-sdk[django]>=1.32.0
newrelic>=8.10.0

# Security
django-cors-headers>=4.2.0
django-environ>=0.10.0
```

### **Nginx Configuration**

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting
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

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Media files
        location /media/ {
            alias /var/www/media/;
            expires 1M;
            add_header Cache-Control "public";
        }

        # API endpoints with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # General application
        location / {
            limit_req zone=general burst=5 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check
        location /health/ {
            proxy_pass http://django;
            access_log off;
        }
    }
}
```

## ☁️ **Cloud Platform Deployment**

### **AWS Deployment with ECS**

#### **Task Definition**
```json
{
  "family": "testimonials-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "your-account.dkr.ecr.region.amazonaws.com/testimonials:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "False"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:testimonials/database"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:testimonials/django"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/testimonials",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health/ || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### **CloudFormation Template**
```yaml
# cloudformation.yml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Django Testimonials Production Stack'

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
  DomainName:
    Type: String
    Default: testimonials.example.com

Resources:
  # ALB Security Group
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for Application Load Balancer
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

  # ECS Security Group
  ECSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for ECS tasks
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          SourceSecurityGroupId: !Ref ALBSecurityGroup

  # Application Load Balancer
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Type: application
      Scheme: internet-facing
      SecurityGroups:
        - !Ref ALBSecurityGroup
      Subnets: !Ref SubnetIds

  # Target Group
  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      HealthCheckPath: /health/
      HealthCheckProtocol: HTTP
      HealthCheckIntervalSeconds: 30
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      Port: 8000
      Protocol: HTTP
      TargetType: ip
      VpcId: !Ref VpcId

  # ECS Cluster
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: testimonials-cluster
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT

  # RDS Instance
  DatabaseInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: testimonials-db
      DBInstanceClass: db.t3.medium
      Engine: postgres
      EngineVersion: '15.3'
      MasterUsername: postgres
      MasterUserPassword: !Ref DatabasePassword
      AllocatedStorage: 20
      StorageType: gp2
      VPCSecurityGroups:
        - !Ref DatabaseSecurityGroup
      DBSubnetGroupName: !Ref DatabaseSubnetGroup
      BackupRetentionPeriod: 7
      MultiAZ: true
      StorageEncrypted: true

  # ElastiCache Redis
  RedisSubnetGroup:
    Type: AWS::ElastiCache::SubnetGroup
    Properties:
      Description: Subnet group for Redis
      SubnetIds: !Ref SubnetIds

  RedisCluster:
    Type: AWS::ElastiCache::ReplicationGroup
    Properties:
      ReplicationGroupDescription: Redis for testimonials
      NumCacheClusters: 2
      Engine: redis
      CacheNodeType: cache.t3.micro
      SubnetGroupName: !Ref RedisSubnetGroup
      SecurityGroupIds:
        - !Ref RedisSecurityGroup
```

### **Google Cloud Platform (GKE)**

#### **Kubernetes Deployment**
```yaml
# k8s-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: testimonials-web
  labels:
    app: testimonials
    component: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: testimonials
      component: web
  template:
    metadata:
      labels:
        app: testimonials
        component: web
    spec:
      containers:
      - name: web
        image: gcr.io/your-project/testimonials:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          value: "False"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: testimonials-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: testimonials-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: testimonials-web-service
spec:
  selector:
    app: testimonials
    component: web
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: testimonials-ingress
  annotations:
    kubernetes.io/ingress.global-static-ip-name: testimonials-ip
    networking.gke.io/managed-certificates: testimonials-ssl-cert
spec:
  rules:
  - host: testimonials.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: testimonials-web-service
            port:
              number: 80
```

### **Azure Container Instances**

#### **ARM Template**
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "containerGroupName": {
      "type": "string",
      "defaultValue": "testimonials-app",
      "metadata": {
        "description": "Name for the container group"
      }
    }
  },
  "resources": [
    {
      "type": "Microsoft.ContainerInstance/containerGroups",
      "apiVersion": "2021-03-01",
      "name": "[parameters('containerGroupName')]",
      "location": "[resourceGroup().location]",
      "properties": {
        "containers": [
          {
            "name": "web",
            "properties": {
              "image": "your-registry.azurecr.io/testimonials:latest",
              "resources": {
                "requests": {
                  "cpu": 1,
                  "memoryInGb": 2
                }
              },
              "ports": [
                {
                  "port": 8000,
                  "protocol": "TCP"
                }
              ],
              "environmentVariables": [
                {
                  "name": "DEBUG",
                  "value": "False"
                }
              ]
            }
          }
        ],
        "osType": "Linux",
        "restartPolicy": "Always",
        "ipAddress": {
          "type": "Public",
          "ports": [
            {
              "protocol": "TCP",
              "port": 8000
            }
          ]
        }
      }
    }
  ]
}
```

## 🔧 **Environment Configuration**

### **Environment Variables Management**

#### **Using django-environ**
```python
# settings/production.py
import environ
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    USE_S3=(bool, True),
    USE_REDIS=(bool, True),
    USE_CELERY=(bool, True),
)

# Read .env file
environ.Env.read_env(BASE_DIR / '.env')

# Core settings
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Database
DATABASES = {
    'default': env.db()
}

# Cache
if env('USE_REDIS'):
    CACHES = {
        'default': env.cache('REDIS_URL')
    }

# Celery
if env('USE_CELERY'):
    CELERY_BROKER_URL = env('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)

# File storage
if env('USE_S3'):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-west-2')

# Testimonials settings
TESTIMONIALS_USE_REDIS_CACHE = env('USE_REDIS')
TESTIMONIALS_USE_CELERY = env('USE_CELERY')
TESTIMONIALS_NOTIFICATION_EMAIL = env('TESTIMONIALS_NOTIFICATION_EMAIL', default=None)
```

#### **.env Template**
```bash
# .env.template
# Copy this file to .env and fill in your values

# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/testimonials

# Cache & Queue
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# File Storage (AWS S3)
USE_S3=True
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-west-2

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Your Site <noreply@yoursite.com>

# Testimonials
TESTIMONIALS_NOTIFICATION_EMAIL=admin@yoursite.com
TESTIMONIALS_MAX_FILE_SIZE=10485760  # 10MB
TESTIMONIALS_CACHE_TIMEOUT=900

# Monitoring
SENTRY_DSN=your-sentry-dsn
NEW_RELIC_LICENSE_KEY=your-new-relic-key

# Performance
USE_REDIS=True
USE_CELERY=True
```

## 📊 **Monitoring & Logging**

### **Logging Configuration**

```python
# settings/logging.py
import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
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
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'sentry': {
            'class': 'sentry_sdk.integrations.logging.SentryHandler',
            'level': 'ERROR',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'testimonials': {
            'handlers': ['console', 'file', 'sentry'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'sentry'],
        'level': 'WARNING',
    },
}
```

### **Prometheus Metrics**

```python
# monitoring.py
from prometheus_client import Counter, Histogram, Gauge
from django.utils.deprecation import MiddlewareMixin

# Metrics
REQUEST_COUNT = Counter(
    'django_requests_total',
    'Total Django requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'django_request_duration_seconds',
    'Django request latency',
    ['method', 'endpoint']
)

TESTIMONIAL_COUNT = Gauge(
    'testimonials_total',
    'Total number of testimonials',
    ['status']
)

class PrometheusMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.resolver_match.url_name if request.resolver_match else 'unknown'
            ).observe(time.time() - request.start_time)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.resolver_match.url_name if request.resolver_match else 'unknown',
            status=response.status_code
        ).inc()

        return response
```

### **Health Checks**

```python
# health_checks.py
import redis
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from celery import current_app

@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """Comprehensive health check endpoint."""
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = {'status': 'healthy'}
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'

    # Redis check
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status['checks']['redis'] = {'status': 'healthy'}
    except Exception as e:
        health_status['checks']['redis'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'

    # Celery check
    try:
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        if stats:
            health_status['checks']['celery'] = {'status': 'healthy'}
        else:
            health_status['checks']['celery'] = {
                'status': 'unhealthy',
                'error': 'No workers available'
            }
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['celery'] = {
            'status': 'unhealthy',
            'error': str(e)
        }

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
```

## 🔐 **Security Configuration**

### **Production Security Settings**

```python
# settings/security.py

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
```

### **Secrets Management**

#### **AWS Secrets Manager**
```python
# utils/secrets.py
import boto3
import json
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name="us-west-2"):
    """Retrieve secret from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

# Usage in settings
if not DEBUG:
    secrets = get_secret('testimonials/production')
    SECRET_KEY = secrets['SECRET_KEY']
    DATABASES['default']['PASSWORD'] = secrets['DB_PASSWORD']
```

## 🚀 **Deployment Automation**

### **GitHub Actions CI/CD**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  release:
    types: [published]

env:
  AWS_REGION: us-west-2
  ECR_REPOSITORY: testimonials

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
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
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
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-django pytest-cov
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_testimonials
        REDIS_URL: redis://localhost:6379/1
      run: |
        pytest --cov=testimonials --cov-report=xml
    
    - name: Upload coverage
      uses: codec# Production Deployment Guide

This guide covers enterprise-grade deployment strategies for Django Testimonials in production environments, including containerization, cloud deployment, and monitoring.

## 🏗️ **Deployment Architecture**

### **Recommended Production Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     CDN         │    │   Monitoring    │
│   (nginx/HAProxy)│    │  (CloudFront)   │    │   (Grafana)     │
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
│   Application   │    │   Background     │    │   File Storage  │
│   (Django)      │◄──►│   (Celery)      │    │   (S3/GCS)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   Cache/Queue   │
│   (PostgreSQL)  │    │   (Redis)       │
└─────────────────┘    └─────────────────┘
```

## 🐳 **Docker Deployment**

### **Dockerfile**

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
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "your_project.wsgi:application