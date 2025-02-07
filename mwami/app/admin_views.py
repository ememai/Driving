from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from django.db.models import Count
from django.http import JsonResponse
from django.contrib import messages
from .models import *
from .forms import *

@staff_member_required
def admin_dashboard(request):
    """
    Displays key statistics and recent records with AJAX updates.
    """
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # AJAX request
        data = {
            'total_users': UserProfile.objects.count(),
            'total_exams': Exam.objects.count(),
            'total_subscriptions': Subscription.objects.count(),
            'active_subscriptions': Subscription.objects.filter(active=True).count(),
            'total_payments': Payment.objects.count(),
            'recent_payments': list(Payment.objects.order_by('-created_at')[:5].values('user__email', 'amount', 'status', 'created_at')),
            'recent_messages': list(ContactMessage.objects.order_by('-created_at')[:5].values('name', 'message', 'created_at')),
        }
        return JsonResponse(data)

    # Regular page load
    form = ScheduledExamForm()
    scheduled_exams = ScheduledExam.objects.all().order_by('-upload_time')

    context = {
        'form': form,
        'scheduled_exams': scheduled_exams,
    }

    return render(request, 'admin_dashboard.html', context)

@staff_member_required
def schedule_exam(request):
    """
    Handles exam scheduling via AJAX.
    """
    if request.method == 'POST':
        form = ScheduledExamForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'message': 'Exam scheduled successfully!'}, status=200)
        return JsonResponse({'error': form.errors}, status=400)
