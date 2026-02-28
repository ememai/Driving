"""
Performance Enhancement Middleware
Provides caching, compression, and optimization for all requests
"""

import time
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)


class CacheMiddleware(MiddlewareMixin):
    """
    Middleware to cache common responses and static data
    """
    CACHEABLE_PATHS = [
        '/exams-list/',
        '/courses/',
        '/exam-types/',
    ]
    
    def process_request(self, request):
        # Skip cache for non-GET requests, authenticated users with specific params
        if request.method != 'GET':
            return None
        
        # Skip cache for authenticated staff members
        if request.user.is_staff:
            return None
        
        # Check if path is cacheable
        for path in self.CACHEABLE_PATHS:
            if request.path.startswith(path):
                cache_key = f"page:{request.path}:{request.GET.urlencode()}"
                cached_response = cache.get(cache_key)
                
                if cached_response:
                    logger.debug(f"Cache HIT for {request.path}")
                    return cached_response
        
        return None
    
    def process_response(self, request, response):
        # Cache successful GET responses
        if request.method == 'GET' and response.status_code == 200:
            for path in self.CACHEABLE_PATHS:
                if request.path.startswith(path):
                    cache_key = f"page:{request.path}:{request.GET.urlencode()}"
                    # Cache for 5 minutes
                    cache.set(cache_key, response, 300)
                    logger.debug(f"Cached response for {request.path}")
        
        return response


class QueryCounterMiddleware(MiddlewareMixin):
    """
    Middleware to log query counts per request (for development/debugging)
    """
    
    def process_request(self, request):
        request._query_start_time = time.time()
        
        # Store initial query count (requires DEBUG=True)
        if hasattr(__import__('django.db', fromlist=['connection']), 'connection'):
            from django.db import connection, reset_queries
            reset_queries()
            request._initial_queries = len(connection.queries)
    
    def process_response(self, request, response):
        if hasattr(request, '_query_start_time'):
            from django.db import connection
            
            duration = time.time() - request._query_start_time
            query_count = len(connection.queries) - getattr(request, '_initial_queries', 0)
            
            # Log if queries are excessive
            if query_count > 10:
                logger.warning(
                    f"High query count ({query_count}) for {request.path} - took {duration:.2f}s"
                )
            
            # Add header with query info (development only)
            if hasattr(__import__('django.conf', fromlist=['settings']), 'DEBUG'):
                response['X-Query-Count'] = str(query_count)
                response['X-Response-Time'] = f"{duration:.2f}s"
        
        return response


class CompressionMiddleware(MiddlewareMixin):
    """
    Middleware to handle content compression and minification
    Already handles by whitenoise and gzip, but this is for reference
    """
    
    def process_response(self, request, response):
        # Ensure gzip compression is enabled for text-based responses
        if response.get('Content-Type', '').startswith(('text/', 'application/json')):
            # This is typically handled by MIDDLEWARE, but ensure it's set
            pass
        
        return response


class PerformanceHeadersMiddleware(MiddlewareMixin):
    """
    Add performance-related headers to all responses
    """
    
    def process_response(self, request, response):
        # Tell browsers to cache static assets longer
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        
        # Security and performance headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-UA-Compatible'] = 'IE=edge'
        
        return response
