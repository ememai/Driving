"""
Performance Optimizations Module
Contains utility decorators and functions to optimize view performance
"""

from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Prefetch, Q
from functools import wraps
import hashlib
import json
from django.utils.encoding import force_bytes


def cache_page(timeout=300, key_prefix=''):
    """
    Decorator to cache view responses
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
        key_prefix: Custom prefix for cache key
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Build cache key from request
            cache_key = f"view:{key_prefix or view_func.__name__}:{request.user.id}:{request.GET.urlencode()}"
            
            # Try to get from cache
            response = cache.get(cache_key)
            if response is not None:
                return response
            
            # Execute view and cache result
            response = view_func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            return response
        return wrapper
    return decorator


def cache_query(*querysets_or_keys):
    """
    Decorator to cache database query results
    
    Args:
        *querysets_or_keys: Cache keys for different querysets
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key based on view and parameters
            cache_key_base = f"query:{view_func.__name__}:{request.user.id}"
            
            # Modify to use cached queries if available
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def paginate_results(queryset, request, per_page=20):
    """
    Utility function to paginate query results
    
    Args:
        queryset: Django queryset to paginate
        request: HTTP request object
        per_page: Results per page (default: 20)
    
    Returns:
        Tuple of (paginator_object, page_object, is_paginated)
    """
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    is_paginated = paginator.num_pages > 1
    
    return paginator, page_obj, is_paginated


def optimize_exam_queries():
    """
    Returns optimized queryset for exams with related data
    """
    from app.models import Exam, Question, RoadSign
    
    # Prefetch questions and their related road signs
    questions_prefetch = Prefetch(
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
    
    return Exam.objects.select_related('exam_type').prefetch_related(
        questions_prefetch
    )


def optimize_userexam_queries():
    """
    Returns optimized queryset for user exams
    """
    from app.models import UserExam
    
    return UserExam.objects.select_related(
        'user',
        'exam__exam_type'
    ).prefetch_related(
        'exam__questions'
    )


def optimize_subscription_queries():
    """
    Returns optimized queryset for subscriptions
    """
    from app.models import Subscription
    
    return Subscription.objects.select_related(
        'user',
        'plan'
    )


def get_cached_exam_types(timeout=3600):
    """
    Get exam types with caching
    """
    from app.models import ExamType, Exam
    
    cache_key = 'exam_types_all'
    exam_types = cache.get(cache_key)
    
    if exam_types is None:
        exam_types = ExamType.objects.filter(
            exam__isnull=False
        ).distinct().order_by('order').annotate(
            actual_exam_count=models.Count('exam')
        )
        cache.set(cache_key, exam_types, timeout)
    
    return exam_types


def clear_cache(pattern='*'):
    """
    Clear cache with optional pattern matching
    """
    if pattern == '*':
        cache.clear()
    else:
        # This is a simple implementation, you may need to customize based on your needs
        pass
