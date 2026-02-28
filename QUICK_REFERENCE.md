# Performance Optimization Quick Reference
## Development Cheat Sheet

---

## 🚀 Quick Commands

```bash
# Start Redis
# Use a local Redis instance in development. The default `REDIS_URL` is
# `redis://127.0.0.1:6379/0`. If you see connection errors to a remote
# host (like turntable.proxy.rlwy.net), update your `.env` or settings.
redis-server

# If you cannot run Redis on Windows, consider using WSL or a Docker container.
# Start Celery Worker
# On Windows prefer the solo pool (`--pool=solo`) or install eventlet/gevent
# for an evented pool (`--pool=eventlet`) after installing the package.
celery -A mwami worker -l info

# Start Celery Beat (Scheduler)
celery -A mwami beat -l info

# Monitor Celery (Dashboard)
celery -A mwami flower

# Run Django
python manage.py runserver

# Apply Migrations
python manage.py migrate

# Collect Static Files
python manage.py collectstatic --noinput
```

---

## 💾 Cache Operations

```python
from django.core.cache import cache

# Set cache
cache.set('key', value, timeout=300)

# Get cache
value = cache.get('key')

# Delete cache
cache.delete('key')

# Clear all cache
cache.clear()

# Get or create
value = cache.get_or_set('key', lambda: expensive_operation(), 3600)
```

---

## 📊 Database Query Optimization

### N+1 Problem

```python
# ❌ BAD (N+1 queries)
exams = Exam.objects.all()
for exam in exams:
    print(exam.exam_type.name)  # Query per exam!

# ✅ GOOD
exams = Exam.objects.select_related('exam_type')
for exam in exams:
    print(exam.exam_type.name)
```

### Joins

```python
# For ForeignKey / OneToOneField
queryset = Model.objects.select_related('foreign_key', 'another_fk')

# For ManyToManyField / Reverse ForeignKey
queryset = Model.objects.prefetch_related('many_to_many', 'reverse_fk')

# Combined
queryset = Model.objects.select_related('fk').prefetch_related('m2m')
```

### Load Specific Fields Only

```python
# Only load needed fields
users = User.objects.only('id', 'name', 'email')

# Exclude heavy fields
courses = Course.objects.defer('description', 'content')

# Get specific values
exam_ids = UserExam.objects.values_list('exam_id', flat=True)
```

### Aggregations

```python
from django.db.models import Count, Sum, Avg, Q

# Count
total = Model.objects.count()

# Annotate
results = Model.objects.annotate(count=Count('relation'))

# Filter and aggregate
data = Model.objects.filter(active=True).aggregate(
    total=Count('id'),
    average_score=Avg('score')
)
```

---

## 🔄 Async Tasks

### Create Task

```python
from celery import shared_task

@shared_task
def my_task(param1, param2):
    # Long-running operation
    return result
```

### Use Task

```python
# Async (non-blocking)
my_task.delay(param1, param2)

# With countdown (delay execution)
my_task.apply_async(args=[param1], countdown=60)

# Get result
result = my_task.delay(param1).get(timeout=10)
```

### Available Tasks

```python
from app.tasks import (
    send_email_task,
    send_otp_email_task,
    send_notification_task,
    check_subscription_expiry,
    send_scheduled_exams_notification,
    auto_schedule_recent_exams_task,
    cleanup_old_data
)

# Use them
send_email_task.delay(subject, message, recipient)
```

---

## 📄 Pagination

```python
from app.performance import paginate_results

# Simple pagination
items = Model.objects.all()
paginator, page_obj, is_paginated = paginate_results(items, request, per_page=20)

# In template
{% for item in page_obj %}
    {{ item }}
{% endfor %}

{% if is_paginated %}
    <nav>
        {% if page_obj.has_previous %}
            <a href="?page=1">First</a>
            <a href="?page={{ page_obj.previous_page_number }}">Previous</a>
        {% endif %}
        
        Page {{ page_obj.number }} of {{ paginator.num_pages }}
        
        {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}">Next</a>
            <a href="?page={{ paginator.num_pages }}">Last</a>
        {% endif %}
    </nav>
{% endif %}
```

---

## ⚡ Cache Patterns

### Cache View Results

```python
def my_view(request):
    cache_key = 'view_result'
    data = cache.get(cache_key)
    
    if data is None:
        data = get_expensive_data()
        cache.set(cache_key, data, 3600)
    
    return render(request, 'template.html', {'data': data})
```

### Cache with Parameters

```python
cache_key = f'user_data:{user_id}'
data = cache.get_or_set(
    cache_key,
    lambda: User.objects.get(id=user_id),
    timeout=3600
)
```

### Invalidate on Save

```python
class MyModel(models.Model):
    name = models.CharField(max_length=100)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'my_model:{self.id}')
        cache.delete('my_model_list')
```

---

## 🔍 Debugging Performance

### Query Counter

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

with CaptureQueriesContext(connection) as context:
    # Your code
    list(Exam.objects.all())

print(len(context.captured_queries))  # Query count
for q in context.captured_queries:
    print(q['sql'])
```

### Django Debug Toolbar

```python
# Install
pip install django-debug-toolbar

# In settings.py (development)
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Restart server and look for toolbar on page
```

### Check Redis

```python
from django_redis import get_redis_connection

redis_conn = get_redis_connection("default")
redis_conn.ping()  # Should return True

# Get stats
info = redis_conn.info()
print(f"Memory: {info['used_memory_human']}")
print(f"Clients: {info['connected_clients']}")
```

---

## 🛡️ Best Practices

### DO ✅

```python
# Use select_related for FK/O2O
Exam.objects.select_related('exam_type')

# Use prefetch_related for M2M
Exam.objects.prefetch_related('questions')

# Paginate large datasets
paginate_results(queryset, request, 20)

# Cache expensive operations
cache.set('key', value, 3600)

# Use async for slow tasks
send_email_task.delay(email)

# Add indexes to frequently queried columns
class Meta:
    indexes = [
        models.Index(fields=['user', 'created_at']),
    ]

# Batch operations
Model.objects.bulk_create(objects)

# Use transactions
@transaction.atomic
def atomic_operation():
    pass
```

### DON'T ❌

```python
# Don't iterate and query
for item in items:
    item.related.method()  # Query in loop!

# Don't load unnecessary fields
Model.objects.all()  # Load everything

# Don't cache too long
cache.set('key', value, 86400)  # Very long

# Don't sync send emails
send_mail(...)  # Blocks request

# Don't query in loops
for id in ids:
    obj = Model.objects.get(id=id)  # Query per id!

# Don't use N-level deep relations in template
{{ obj.fk.fk.fk.field }}  # Multiple queries

# Don't ignore slow query logs
# Monitor and optimize slow queries
```

---

## 🎯 Common Optimization Patterns

### Pattern 1: Get or Create with Cache

```python
def get_or_cache_item(item_id):
    cache_key = f'item:{item_id}'
    return cache.get_or_set(
        cache_key,
        lambda: Model.objects.select_related('fk').get(id=item_id),
        timeout=3600
    )
```

### Pattern 2: Batch Read + Cache

```python
def get_items_cached(ids):
    cache_key = f'items:{",".join(map(str, ids))}'
    items = cache.get(cache_key)
    
    if items is None:
        items = Model.objects.filter(id__in=ids)
        cache.set(cache_key, items, 3600)
    
    return items
```

### Pattern 3: Async Email with Fallback

```python
def send_notification(user, message):
    try:
        send_email_task.delay(user.email, message)
    except Exception:
        # Fallback to sync if celery fails
        send_mail_sync(user.email, message)
```

### Pattern 4: Invalidate Related Caches

```python
def update_model(instance, **changes):
    for field, value in changes.items():
        setattr(instance, field, value)
    instance.save()
    
    # Invalidate caches
    cache.delete(f'item:{instance.id}')
    cache.delete('items_list')
    cache.delete(f'user_items:{instance.user_id}')
```

---

## 📊 Monitoring

### Check Cache Stats

```python
from django_redis import get_redis_connection

redis = get_redis_connection("default")
stats = redis.info()

print(f"Keys: {stats['db0']['keys']}")
print(f"Memory: {stats['used_memory_human']}")
print(f"Hits: {stats.get('keyspace_hits', 0)}")
print(f"Misses: {stats.get('keyspace_misses', 0)}")
```

### Celery Task Status

```bash
# Check active tasks
celery -A mwami inspect active

# Check task stats
celery -A mwami inspect stats

# Monitor in real-time
celery -A mwami flower
```

### Database Performance

```python
# Enable logging in settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    },
}
```

---

## 🚨 Troubleshooting

### Redis Connection Failed

```bash
# Check Redis is running
redis-cli ping

# Check connection string
REDIS_URL=redis://127.0.0.1:6379/0

# Test from Python
from django_redis import get_redis_connection
redis_conn = get_redis_connection("default")
redis_conn.ping()
```

### Celery Tasks Not Running

```bash
# Check worker is running
celery -A mwami inspect active

# Check broker connection
celery -A mwami inspect ping

# Check task is registered
celery -A mwami inspect registered
```

### Cache Not Working

```python
# Clear cache
from django.core.cache import cache
cache.clear()

# Test cache
cache.set('test', 'value', 60)
print(cache.get('test'))  # Should print 'value'
```

---

## 📚 More Information

- **PERFORMANCE_GUIDE.md** - Comprehensive guide (4000+ lines)
- **IMPLEMENTATION_GUIDE.md** - Setup instructions
- **app/optimized_views.py** - Code examples
- **Django Docs** - https://docs.djangoproject.com/
- **Redis Docs** - https://redis.io/docs/
- **Celery Docs** - https://docs.celeryproject.org/

---

## ⏱️ Quick Response Time Targets

| Component | Target |
|-----------|--------|
| Page Load | < 2 seconds |
| API Call | < 500ms |
| Cache Hit | < 50ms |
| Database Query | < 100ms |
| Email Send | Async (users don't wait) |
| Task Processing | < 1 minute |

---

**Print this page for quick reference!**
Last updated: February 2026
