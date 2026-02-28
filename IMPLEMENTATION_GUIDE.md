"""
IMPLEMENTATION GUIDE FOR PERFORMANCE OPTIMIZATIONS
Quick start guide for developers
"""

# ==============================================================================
# 1. BEFORE DEPLOYING - RUN MIGRATIONS
# ==============================================================================

# Apply database indexes
python manage.py migrate app 0008_optimize_indexes

# Collect static files
python manage.py collectstatic --noinput


# ==============================================================================
# 2. INSTALL NEW DEPENDENCIES
# ==============================================================================

pip install -r requirements.txt

# Specifically:
# - django-redis: Redis caching backend
# - celery: Async task queue
# - channels-redis: For Channels in production
# - django-debug-toolbar: For development debugging (optional)
# - flower: For monitoring Celery tasks (optional)


# ==============================================================================
# 3. START REDIS SERVER (REQUIRED)
# ==============================================================================

# Windows (WSL recommended):
# Install Redis from: https://github.com/microsoftarchive/redis/releases
# OR use WSL:
wsl
sudo apt-get install redis-server
redis-server

# macOS:
brew install redis
redis-server

# Docker:
docker run -d -p 6379:6379 redis:latest


# ==============================================================================
# 4. START CELERY WORKERS
# ==============================================================================

# **Important (Windows Users)**
# Celery's default prefork pool uses semaphores which often fail on Windows
# leading to PermissionError. Choose a simpler pool or run inside WSL/Linux.
#
# Use solo pool for development on Windows:
# ```bash
# celery -A mwami worker -l info --pool=solo
# ```
# For higher concurrency install an evented pool.
# ```bash
# pip install eventlet    # recommended and works on Windows
# # pip install gevent     # optional; may fail to build on Windows
# celery -A mwami worker -l info --pool=eventlet
# ```
# Avoid the default pool when you see `[WinError 5] Access is denied`.

# Terminal 1: Celery Worker (Main Queue)
celery -A mwami worker -l info
# (Add `--pool=solo` on Windows)

# Terminal 2: Celery Beat (Scheduler for periodic tasks)
celery -A mwami beat -l info

# Optional Terminal 3: Flower (Web UI for monitoring)
celery -A mwami flower


# ==============================================================================
# 5. CONFIGURATION IN .env
# ==============================================================================

# Add to your .env file:

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1


# ==============================================================================
# 6. MIDDLEWARE CONFIGURATION
# ==============================================================================

# Already added to MIDDLEWARE in settings.py:
# - app.performance_middleware.CacheMiddleware
# - app.performance_middleware.QueryCounterMiddleware
# - app.performance_middleware.PerformanceHeadersMiddleware


# ==============================================================================
# 7. EXAMPLE: USING CACHE IN VIEWS
# ==============================================================================

from django.core.cache import cache
from app.performance import paginate_results

def my_view(request):
    # Method 1: Simple cache
    cache_key = 'my_data'
    data = cache.get(cache_key)
    
    if data is None:
        data = expensive_operation()
        cache.set(cache_key, data, 300)  # Cache for 5 minutes
    
    return render(request, 'template.html', {'data': data})


def list_view(request):
    # Method 2: Pagination for large datasets
    items = Model.objects.select_related('foreign_key').all()
    paginator, page_obj, is_paginated = paginate_results(items, request, per_page=20)
    
    context = {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': is_paginated,
    }
    return render(request, 'list.html', context)


# ==============================================================================
# 8. EXAMPLE: ASYNC TASKS WITH CELERY
# ==============================================================================

# Instead of:
from django.core.mail import send_mail
send_mail(subject, message, from_email, [recipient])  # Blocks request!

# Use:
from app.tasks import send_email_task
send_email_task.delay(subject, message, [recipient])  # Returns immediately


# ==============================================================================
# 9. EXAMPLE: DATABASE QUERY OPTIMIZATION
# ==============================================================================

# Bad (N+1 queries):
exams = Exam.objects.all()
for exam in exams:
    print(exam.exam_type.name)  # Extra query per exam!

# Good (Optimized):
from django.db.models import Prefetch

exams = Exam.objects.select_related('exam_type').prefetch_related(
    Prefetch(
        'questions',
        Question.objects.select_related('question_type', 'question_sign')
    )
)

for exam in exams:
    print(exam.exam_type.name)  # No extra queries!


# ==============================================================================
# 10. INTEGRATION STEPS FOR EXISTING VIEWS
# ==============================================================================

# Step 1: Replace view function with optimized version from optimized_views.py
# Example:
#   OLD: from app import views; exams_by_type = views.exams_by_type
#   NEW: from app.optimized_views import exams_by_type_optimized as exams_by_type

# Step 2: Update URLs to use new views
# In urls.py:
#   OLD: path('exams/<str:exam_type>/', views.exams_by_type, name='exams_by_type')
#   NEW: path('exams/<str:exam_type>/', optimized_views.exams_by_type_optimized, name='exams_by_type')

# Step 3: Test and validate
# - Check query count in Django Debug Toolbar
# - Monitor response time
# - Verify cache hits


# ==============================================================================
# 11. CACHE INVALIDATION
# ==============================================================================

# When data changes, invalidate related caches:

from django.core.cache import cache

def update_exam(exam_id, **changes):
    exam = Exam.objects.get(id=exam_id)
    
    # Update the object
    for field, value in changes.items():
        setattr(exam, field, value)
    exam.save()
    
    # Invalidate caches that depend on this exam
    cache.delete(f'exam_questions:{exam_id}')
    cache.delete('home_page_data')
    cache.delete('navbar_exam_types')


# ==============================================================================
# 12. MONITORING PERFORMANCE
# ==============================================================================

# Development: Use Django Debug Toolbar
# Install: pip install django-debug-toolbar
# Configure in settings.py (already done for DEBUG=True)

# Production: Monitor metrics
# - Query execution time: Check database logs
# - Cache hit rate: Check Redis stats
# - Celery task success: Check Flower dashboard
# - Page response time: Use APM tools (New Relic, DataDog, etc.)


# ==============================================================================
# 13. PRODUCTION DEPLOYMENT CHECKLIST
# ==============================================================================

# Before going live:

# ✓ Set DEBUG = False in settings.py
# ✓ Configure Redis with persistence
# ✓ Set up Celery workers with process manager (supervisord, systemd)
# ✓ Configure Celery Beat scheduler
# ✓ Set up monitoring and alerting
# ✓ Configure automated backups for Redis
# ✓ Test under load with realistic data volume
# ✓ Set up log aggregation
# ✓ Configure database connection pooling
# ✓ Enable slow query logging in database

# Example supervisor configuration for Celery:
"""
[program:celery_worker]
command=celery -A mwami worker -l info -c 4
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10

[program:celery_beat]
command=celery -A mwami beat -l info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.log
autostart=true
autorestart=true
startsecs=10
"""


# ==============================================================================
# 14. TROUBLESHOOTING
# ==============================================================================

# Issue: Redis connection refused
# Solution: Ensure Redis is running and accessible
redis-cli ping  # Should return PONG

# Issue: Celery tasks not executing
# Solution: Check worker is running and connected to broker
celery -A mwami inspect active

# Issue: Cache not working
# Solution: Clear cache and test
from django.core.cache import cache
cache.clear()

# Issue: High query count on specific view
# Solution: Use Django Debug Toolbar to identify N+1 queries
# Add select_related() or prefetch_related() accordingly


# ==============================================================================
# 15. PERFORMANCE TESTING
# ==============================================================================

# Load testing with Apache Bench:
ab -n 1000 -c 10 http://localhost:8000/

# Load testing with wrk:
wrk -t12 -c400 -d30s http://localhost:8000/

# Profile Django views:
# Install: pip install django-silk
# Add to INSTALLED_APPS and MIDDLEWARE
# Access: http://localhost:8000/silk/


# ==============================================================================
# 16. COMMON OPTIMIZATION PATTERNS
# ==============================================================================

# Pattern 1: Cache frequently accessed configuration
CONFIG_CACHE_KEY = 'app_config'
def get_app_config():
    config = cache.get(CONFIG_CACHE_KEY)
    if config is None:
        config = {
            'max_attempts': settings.MAX_LOGIN_ATTEMPTS,
            'cache_timeout': settings.CACHE_TIMEOUT,
        }
        cache.set(CONFIG_CACHE_KEY, config, 86400)
    return config

# Pattern 2: Lazy load related objects
def get_user_with_subscription(user_id):
    user = User.objects.get(id=user_id)
    if request.needs_subscription_info:
        user = User.objects.select_related('subscription').get(id=user_id)
    return user

# Pattern 3: Batch operations
users = User.objects.filter(status='active')
User.objects.filter(id__in=users).update(last_checked=now)

# Pattern 4: Archive old data
OLD_RECORDS = UserActivity.objects.filter(
    timestamp__lt=timezone.now() - timedelta(days=90)
)
# Archive or delete as needed


# ==============================================================================
# 17. CONTACTS & SUPPORT
# ==============================================================================

# For questions about performance:
# 1. Check PERFORMANCE_GUIDE.md for detailed documentation
# 2. Review app/optimized_views.py for examples
# 3. Use Django Debug Toolbar in development
# 4. Monitor Flower dashboard in production

print("""
✅ Performance optimization setup complete!

Next steps:
1. Start Redis server
2. Run migrations
3. Install dependencies
4. Start Celery worker and beat
5. Run development server
6. Monitor with Django Debug Toolbar

Questions? Check PERFORMANCE_GUIDE.md
""")
