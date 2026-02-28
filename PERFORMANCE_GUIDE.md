# Django Performance Optimization Guide
## Kigali Driving School Project

---

## Table of Contents
1. [Caching Configuration](#caching-configuration)
2. [Database Query Optimization](#database-query-optimization)
3. [Async Tasks with Celery](#async-tasks-with-celery)
4. [Query Performance Monitoring](#query-performance-monitoring)
5. [Best Practices](#best-practices)
6. [Implementation Checklist](#implementation-checklist)

---

## 1. Caching Configuration

### Redis Setup

Redis is configured in `settings.py` and provides distributed caching. To enable it:

```bash
# Install Redis server (Windows)
# Download from: https://github.com/microsoftarchive/redis/releases

# Or use WSL:
sudo apt-get install redis-server

# Start Redis
redis-server
```

### Cache Timeout Settings (in seconds)

```python
CACHE_TIMEOUT_SHORT = 60          # 1 minute
CACHE_TIMEOUT_MEDIUM = 300        # 5 minutes
CACHE_TIMEOUT_LONG = 3600         # 1 hour
CACHE_TIMEOUT_EXTRA_LONG = 86400  # 24 hours
```

### Using Cache in Views

```python
from django.core.cache import cache

# Simple caching
cache.set('key', value, timeout=300)
value = cache.get('key')

# With decorator
from app.performance import cache_page

@cache_page(timeout=3600, key_prefix='home')
def home_view(request):
    # View code here
    pass
```

### Cache Invalidation

```python
# Clear specific cache
cache.delete('cache_key')

# Clear all cache
cache.clear()

# Clear with pattern (use django-redis)
from django_redis import get_redis_connection
redis_conn = get_redis_connection("default")
redis_conn.delete_pattern('kds:*')
```

---

## 2. Database Query Optimization

### N+1 Query Problem

**Bad (N+1 queries):**
```python
exams = Exam.objects.all()
for exam in exams:
    print(exam.exam_type.name)  # Additional query per exam!
```

**Good (Optimized):**
```python
from django.db.models import Prefetch

exams = Exam.objects.select_related('exam_type')
for exam in exams:
    print(exam.exam_type.name)  # No additional queries!
```

### Key Optimization Techniques

#### 1. **select_related()** - For ForeignKey and OneToOneField
```python
# Single query instead of N queries
queryset = UserExam.objects.select_related('user', 'exam__exam_type')
```

#### 2. **prefetch_related()** - For ManyToManyField and reverse ForeignKey
```python
# Optimized queries for relationships
exams = Exam.objects.prefetch_related('questions', 'scheduledexam_set')
```

#### 3. **Prefetch with Prefetch Object** - Advanced optimization
```python
from django.db.models import Prefetch

questions_prefetch = Prefetch(
    'questions',
    Question.objects.select_related('question_type', 'question_sign')
)

exams = Exam.objects.select_related('exam_type').prefetch_related(questions_prefetch)
```

#### 4. **only() and defer()** - Load specific fields only
```python
# Only load necessary fields
users = UserProfile.objects.only('id', 'name', 'email')

# Good for large text fields
courses = Course.objects.defer('description')
```

#### 5. **values() and values_list()** - For aggregate queries
```python
# Don't load full objects if you only need specific fields
exam_ids = UserExam.objects.filter(user=user).values_list('exam_id', flat=True)

# Avoid:
UserExam.objects.filter(user=user).values_list('id')  # Returns list of tuples
```

### Query Optimization Examples

**Home View:**
```python
# Bad: Multiple queries for exam types and counts
exam_types = ExamType.objects.all()

# Good: Single query with annotation
from django.db.models import Count, Prefetch

exam_types = ExamType.objects.filter(
    exam__isnull=False
).distinct().order_by('order').annotate(
    actual_exam_count=Count('exam')
).prefetch_related(
    Prefetch('exam_set', Exam.objects.filter(is_active=True))
)
```

**Exams by Type:**
```python
# Optimized query
exams = Exam.objects.filter(
    exam_type__name=exam_type
).select_related('exam_type').prefetch_related(
    Prefetch(
        'questions',
        Question.objects.select_related(
            'question_type',
            'question_sign',
            'choice1_sign',
            'choice2_sign',
            'choice3_sign',
            'choice4_sign'
        )
    )
).order_by('-updated_at')
```

---

## 3. Async Tasks with Celery

### Setup

1. **Configure in settings.py:**
   ```python
   CELERY_BROKER_URL = REDIS_URL
   CELERY_RESULT_BACKEND = REDIS_URL
   ```

2. **Start Celery worker:**
   ```bash
   celery -A mwami worker -l info -Q default,email,exams,notifications
   ```

3. **Start Celery beat (scheduler):**
   ```bash
   celery -A mwami beat -l info
   ```

### Creating Async Tasks

```python
from celery import shared_task
from django.core.mail import send_mail

@shared_task(bind=True, max_retries=3)
def send_email_task(self, subject, message, recipient):
    try:
        send_mail(subject, message, 'from@example.com', [recipient])
        return f"Email sent to {recipient}"
    except Exception as exc:
        self.retry(exc=exc)
```

### Using Tasks in Views

```python
# Instead of blocking:
send_mail(...)  # Blocks the user's request

# Use async:
from app.tasks import send_email_task
send_email_task.delay(subject, message, recipient)  # Returns immediately
```

### Available Tasks

1. **Email Tasks:**
   - `send_email_task()` - Generic email sending
   - `send_otp_email_task()` - Send OTP codes
   - `send_subscription_confirmation_task()` - Subscription emails

2. **Notification Tasks:**
   - `send_notification_task()` - In-app notifications
   - `send_scheduled_exams_notification()` - Exam reminders

3. **Subscription Tasks:**
   - `check_subscription_expiry()` - Daily check for expiring subscriptions
   - `send_subscription_confirmation_task()` - Subscription confirmations

4. **Exam Tasks:**
   - `auto_schedule_recent_exams_task()` - Auto-schedule exams
   - `cleanup_old_data()` - Weekly data cleanup

---

## 4. Database Indexes

Indexes have been added to frequently queried columns:

```python
# UserProfile
- phone_number
- email
- is_active

# Subscription
- user, expires_at, otp_verified

# Exam
- exam_type + for_scheduling, created_at, is_active

# ScheduledExam
- scheduled_datetime, exam

# UserExam
- user + exam, completed_at, user + completed_at

# Course
- slug, category

# Question
- question_type, order

# Payment
- user, created_at
```

Apply migration:
```bash
python manage.py migrate app 0008_optimize_indexes
```

---

## 5. Query Performance Monitoring

### Enable Query Logging

Add to settings.py for development:
```python
if DEBUG:
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
                'handlers': ['console'],
                'level': 'DEBUG',
            },
        },
    }
```

### Query Counter During Development

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

with CaptureQueriesContext(connection) as context:
    # Your code here
    list(Exam.objects.all())

print(f"Number of queries: {len(context.captured_queries)}")
for query in context.captured_queries:
    print(query['sql'])
```

### Django Debug Toolbar

Install for development:
```bash
pip install django-debug-toolbar
```

Add to settings.py:
```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

---

## 6. Best Practices

### 1. Always Use Pagination for List Views

```python
from app.performance import paginate_results

def my_view(request):
    items = MyModel.objects.all()
    paginator, page_obj, is_paginated = paginate_results(items, request, per_page=20)
    
    context = {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': is_paginated,
    }
    return render(request, 'template.html', context)
```

### 2. Cache Expensive Computations

```python
def get_user_stats(user):
    cache_key = f'user_stats:{user.id}'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Expensive computation
        stats = {
            'exams_taken': UserExam.objects.filter(user=user).count(),
            'avg_score': UserExam.objects.filter(user=user).aggregate(Avg('score'))
        }
        cache.set(cache_key, stats, 3600)
    
    return stats
```

### 3. Use Database Transactions for Consistency

```python
from django.db import transaction

@transaction.atomic
def complex_operation(user):
    subscription = Subscription.objects.create(...)
    Payment.objects.create(...)
    # If any error occurs, all changes are rolled back
```

### 4. Batch Operations

```python
# Bad: Multiple saves
for user in users:
    user.last_login = now
    user.save()  # Query per user!

# Good: Batch update
User.objects.filter(id__in=user_ids).update(last_login=now)

# Good: Bulk create
users_to_create = [User(...), User(...), ...]
User.objects.bulk_create(users_to_create)
```

### 5. Lazy Load Related Objects When Needed

```python
# Setup QuerySet
exams = Exam.objects.all()

# Add select_related dynamically if needed
if request.GET.get('with_questions'):
    exams = exams.prefetch_related('questions')

return render(request, 'exams.html', {'exams': exams})
```

### 6. Monitor and Cache Session Data

```python
# Instead of querying every time
user.subscription.status  # N queries

# Cache it
def get_subscription_status(user):
    key = f'sub_status:{user.id}'
    status = cache.get(key)
    if status is None:
        status = user.subscription.status if hasattr(user, 'subscription') else None
        cache.set(key, status, 300)
    return status
```

---

## 7. Implementation Checklist

- [x] Redis caching configured
- [x] Celery task queue setup
- [x] Database indexes added
- [x] Optimization utilities created (performance.py)
- [x] Optimized view examples provided (optimized_views.py)
- [ ] Apply to all views in app/views.py
- [ ] Replace context processors with cached queries
- [ ] Add pagination to all list views
- [ ] Test with Django Debug Toolbar
- [ ] Monitor query counts in production
- [ ] Set up Celery monitoring (Flower)
- [ ] Configure automatic cache invalidation on data changes

---

## 8. Deployment Configuration

### Production Settings

```python
# settings.py
if not DEBUG:
    # Connection pooling
    DATABASES['default']['CONN_MAX_AGE'] = 600
    
    # Redis with persistence
    CACHES['default']['OPTIONS']['CONNECTION_POOL_KWARGS']['max_connections'] = 50
    
    # Celery with concurrency
    CELERY_WORKER_CONCURRENCY = 4
    
    # Static files
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### Docker Commands

```bash
# Start Redis
docker run -d -p 6379:6379 redis:latest

# Start Celery Worker (3 concurrent processes)
docker run -e DJANGO_SETTINGS_MODULE=mwami.settings celery -A mwami worker -c 3

# Start Celery Beat
docker run -e DJANGO_SETTINGS_MODULE=mwami.settings celery -A mwami beat

# Monitor with Flower
docker run -p 5555:5555 mher/flower celery flower -A mwami --broker=redis://redis:6379
```

---

## 9. Performance Targets

- **Page Load Time:** < 2 seconds
- **Database Query Time:** < 100ms per page
- **Cache Hit Rate:** > 80%
- **API Response Time:** < 500ms
- **Celery Task Success Rate:** > 99%

---

## 10. Troubleshooting

### Redis Connection Issues

```python
# Test connection
from django_redis import get_redis_connection
redis_conn = get_redis_connection("default")
redis_conn.ping()  # Should return True
```

### Celery Not Processing Tasks

```bash
# Check worker logs
celery -A mwami worker -l debug

# Check result backend
celery -A mwami events
```

### Database Locks

```python
# Use select_for_update() for critical sections
with transaction.atomic():
    user = UserProfile.objects.select_for_update().get(id=user_id)
    # Perform operations
```

---

## Additional Resources

- [Django Caching Documentation](https://docs.djangoproject.com/en/5.1/topics/cache/)
- [Django Query Optimization](https://docs.djangoproject.com/en/5.1/ref/models/querysets/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/docs/)
- [Django Database Access Optimization](https://docs.djangoproject.com/en/5.1/topics/db/optimization/)

