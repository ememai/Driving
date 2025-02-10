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