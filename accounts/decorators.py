"""
Custom decorators for cache control and authentication.
Prevents browser and server-side caching for user-specific views.
"""

from functools import wraps
from django.views.decorators.cache import never_cache as django_never_cache
from django.utils.decorators import decorator_from_middleware
from django.middleware.cache import CacheMiddleware


def never_cache(view_func):
    """
    Decorator that adds headers to prevent all caching (browser and server-side).
    Use this for all user-specific views to ensure real-time data updates.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # Add cache control headers to prevent browser caching
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Vary'] = 'Cookie, Authorization'
        
        return response
    
    return django_never_cache(_wrapped_view)


def no_cache_for_authenticated(view_func):
    """
    Decorator that prevents caching only for authenticated users.
    Anonymous users can still benefit from caching.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        if request.user.is_authenticated:
            # Prevent caching for authenticated users
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Vary'] = 'Cookie, Authorization'
        
        return response
    
    return _wrapped_view


# Cache control middleware for class-based views
class DisableClientSideCachingMiddleware:
    """
    Middleware to disable client-side caching for all responses.
    Add to MIDDLEWARE after AuthenticationMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only disable caching for authenticated users on dynamic pages
        if request.user.is_authenticated and 'text/html' in response.get('Content-Type', ''):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Vary'] = 'Cookie, Authorization'
        
        return response
