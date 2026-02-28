# app/context_processors.py
from django.utils import timezone
from django.core.cache import cache
from .models import *
from .utils import *


def unverified_subscription_context(request):
    """
    Get unverified subscription with caching
    """
    if not request.user.is_authenticated:
        return {'unverified_subscription': None}
    
    # Cache per user for 5 minutes
    cache_key = f'unverified_sub:{request.user.id}'
    # try to fetch cached value; the cache stores a Subscription instance or None
    subscription = cache.get(cache_key)

    # if we hit the cache we still have to make sure the entry is still valid
    # because the underlying subscription may have been verified/changed since
    # it was cached.  stale objects would cause the modal to appear even after
    # the user activates the OTP (or conversely disappear prematurely).  the
    # signal handler below takes care of clearing the cache on every save,
    # but defending here helps in case a backend evicts the key and the
    # subsequent lookup returns an out‑of‑date instance.
    if subscription is not None:
        # subscription is either a model instance or None; if it's the former
        # double‑check that it still matches our criteria.
        if subscription and (
                subscription.otp_verified or
                subscription.user_id != request.user.id):
            # treat as cache miss
            subscription = None
            cache.delete(cache_key)

    if subscription is None:
        subscription = get_unverified_subscription(request.user)
        # store even None so we avoid hitting the database repeatedly when
        # there is no unverified record; the TTL is small and we always clear
        # the key from our signal handlers when anything interesting happens.
        cache.set(cache_key, subscription, 300)

    return {'unverified_subscription': subscription}


def exams_slider_context(request):
    """
    Get scheduled exams for slider with caching
    Caches for 30 minutes since exams are scheduled in advance
    """
    cache_key = 'exams_slider_context'
    context = cache.get(cache_key)
    
    if context is None:
        now = timezone.localtime(timezone.now())
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        context = {
            'exams_scheduled': ScheduledExam.objects.filter(
                scheduled_datetime__range=(start_of_day, end_of_day)
            ).select_related('exam', 'exam__exam_type'),
        }
        
        # Cache for 30 minutes
        cache.set(cache_key, context, 1800)
    
    return context