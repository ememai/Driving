
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

def is_social_bot(user_agent):
    # List of known social bot user agents
    social_bots = [
        'facebookexternalhit',
        'Twitterbot',
        'LinkedInBot',
        'Pinterest/0.7',
        'Slackbot',
        'WhatsApp'
    ]
    
    # Check if the user agent contains any of the social bot identifiers
    return any(bot.lower() in user_agent.lower() for bot in bots)
class BotBypassMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not is_social_bot(request.META.get('HTTP_USER_AGENT', '')):
            # Optional: redirect or block logic here
            pass
        return self.get_response(request)
