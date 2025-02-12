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
