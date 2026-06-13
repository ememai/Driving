
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import redirect
import time
from django.utils.deprecation import MiddlewareMixin

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
    return any(bot.lower() in user_agent.lower() for bot in social_bots)

class BotBypassMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not is_social_bot(request.META.get('HTTP_USER_AGENT', '')):
            # Optional: redirect or block logic here
            pass
        return self.get_response(request)


class TrafficLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all HTTP traffic to the TrafficLog model with detailed visitor data"""
    
    def process_request(self, request):
        # Store the start time in request
        request._traffic_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        # Calculate response time
        if hasattr(request, '_traffic_start_time'):
            response_time = (time.time() - request._traffic_start_time) * 1000  # Convert to ms
        else:
            response_time = 0.0
        
        # Skip logging for static files and media
        skip_paths = ['/static/', '/media/', '/favicon.ico', '/.well-known/']
        if any(request.path.startswith(path) for path in skip_paths):
            return response
        
        # Log traffic asynchronously to avoid blocking response
        try:
            from app.models import TrafficLog
            
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            referrer = request.META.get('HTTP_REFERER', '')[:500] if request.META.get('HTTP_REFERER') else None
            
            # Parse user agent for device and browser info
            device_info = self.parse_user_agent(user_agent)
            
            # Determine traffic platform/source
            platform = self.determine_platform(referrer, user_agent)
            
            # Get location from IP (optional - requires geoip data)
            location_data = self.get_location_data(ip_address)
            
            TrafficLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                path=request.path[:500],
                method=request.method,
                status_code=response.status_code,
                ip_address=ip_address,
                
                # Location
                country=location_data.get('country'),
                city=location_data.get('city'),
                country_code=location_data.get('country_code'),
                
                # Device info
                device_type=device_info.get('device_type'),
                device_name=device_info.get('device_name'),
                browser=device_info.get('browser'),
                browser_version=device_info.get('browser_version'),
                os=device_info.get('os'),
                os_version=device_info.get('os_version'),
                
                # Traffic source
                platform=platform,
                
                # User agent and referrer
                user_agent=user_agent,
                referrer=referrer,
                response_time=response_time
            )
        except Exception as e:
            # Silently fail to avoid breaking the request
            pass
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address from the request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def parse_user_agent(user_agent):
        """Parse user agent to extract device, browser, and OS information"""
        try:
            from user_agents import parse
            ua = parse(user_agent)
            
            # Determine device type
            if ua.is_mobile:
                device_type = 'mobile'
            elif ua.is_tablet:
                device_type = 'tablet'
            elif ua.is_pc:
                device_type = 'desktop'
            else:
                device_type = 'unknown'
            
            # Determine OS
            os_name = ua.os.family.lower() if ua.os.family else 'unknown'
            if 'windows' in os_name:
                os = 'windows'
            elif 'mac' in os_name:
                os = 'macos'
            elif 'linux' in os_name:
                os = 'linux'
            elif 'ios' in os_name or 'iphone' in os_name or 'ipad' in os_name:
                os = 'ios'
            elif 'android' in os_name:
                os = 'android'
            else:
                os = 'unknown'
            
            return {
                'device_type': device_type,
                'device_name': ua.device.family or None,
                'browser': ua.browser.family or None,
                'browser_version': ua.browser.version_string or None,
                'os': os,
                'os_version': ua.os.version_string or None,
            }
        except ImportError:
            # If user_agents not installed, return defaults
            return {
                'device_type': 'unknown',
                'device_name': None,
                'browser': None,
                'browser_version': None,
                'os': 'unknown',
                'os_version': None,
            }
        except Exception:
            return {
                'device_type': 'unknown',
                'device_name': None,
                'browser': None,
                'browser_version': None,
                'os': 'unknown',
                'os_version': None,
            }
    
    @staticmethod
    def determine_platform(referrer, user_agent):
        """Determine traffic platform/source from referrer and user agent"""
        if not referrer:
            return 'direct'
        
        referrer_lower = referrer.lower()
        
        # Check for specific platforms
        if 'whatsapp' in referrer_lower or 'whatsapp' in user_agent.lower():
            return 'whatsapp'
        elif 'facebook' in referrer_lower or 'fb' in referrer_lower:
            return 'facebook'
        elif 'twitter' in referrer_lower or 'x.com' in referrer_lower:
            return 'twitter'
        elif 'instagram' in referrer_lower:
            return 'instagram'
        elif 'linkedin' in referrer_lower:
            return 'linkedin'
        elif 'google' in referrer_lower:
            return 'google'
        elif 'mail' in referrer_lower or 'email' in referrer_lower:
            return 'email'
        else:
            return 'other'
    
    @staticmethod
    def get_location_data(ip_address):
        """Get location data from IP address"""
        location_data = {
            'country': None,
            'city': None,
            'country_code': None,
        }
        
        if not ip_address or ip_address.startswith('127.'):
            return location_data
        
        try:
            # Try using geoip2 if available
            try:
                from django.contrib.gis.geoip2 import GeoIP2
                g = GeoIP2()
                geoip_data = g.city(ip_address)
                location_data['country'] = geoip_data.get('country_name')
                location_data['city'] = geoip_data.get('city')
                location_data['country_code'] = geoip_data.get('country_code')
            except Exception:
                # If GeoIP2 not available or fails, try ip-api
                try:
                    import requests
                    response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'success':
                            location_data['country'] = data.get('country')
                            location_data['city'] = data.get('city')
                            location_data['country_code'] = data.get('countryCode')
                except Exception:
                    pass
        except Exception:
            pass
        
        return location_data

