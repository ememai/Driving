
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import redirect

class SubscriptionMiddleware:
    def process_view(self, request, view_func, view_args, view_kwargs):
        protected_paths = [
            '/exam/',
            '/exams/',
            '/exam-timer/'
        ]
        
        if any(request.path.startswith(path) for path in protected_paths):
            if not request.user.is_authenticated:
                return redirect('login')
            if not request.user.is_subscribed():
                return redirect('subscription')


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Check if the request path starts with '/admin/'
        if request.path.startswith('/admin/'):
            # If user is not authenticated or not a staff member, redirect
            if not (request.user.is_authenticated and request.user.is_staff):
                return HttpResponseRedirect(reverse('home'))  # Redirect to home or a 403 page

        return response


# class ExamSecurityMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         response = self.get_response(request)
        
#         if request.path.startswith('/exam/'):
#             # Prevent back button after submission
#             response['Cache-Control'] = 'no-store, must-revalidate'
#             response['Pragma'] = 'no-cache'
#             response['Expires'] = '0'
            
#         return response
