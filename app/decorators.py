from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from functools import wraps
from .models import *

from django.contrib.auth.decorators import login_required, permission_required
import logging

logger = logging.getLogger(__name__)

def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@permission_required('app_name.can_edit_page')
def edit_view(request):
    return render(request, 'edit_page.html')

def subscription_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        first_exam = Exam.objects.filter(exam_type__name__icontains='ibivanze').order_by('created_at').first()
        exam_id = kwargs.get('exam_id') or kwargs.get('pk')
        
        print(f"First Exam ID: {first_exam.id if first_exam else 'None'}")
        print(f"Requested Exam ID: {exam_id}")
        
        if not request.user.is_subscribed and not request.user.is_staff:
            if first_exam and exam_id and str(exam_id) == str(first_exam.id):
                return view_func(request, *args, **kwargs)
            messages.error(request, "Gura ifatabuguzi kugirango ubashe gukomeza!")
            return redirect('subscription')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def redirect_authenticated_users(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')  # Redirect to the home page or any other page
        return view_func(request, *args, **kwargs)
    return _wrapped_view