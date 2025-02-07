# admin_views.py
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from django.db.models import Count
from .models import *
from .forms import *

@staff_member_required  
def admin_dashboard(request):
    """
    Displays key statistics and recent records.
    """
    # Gather overview statistics
    total_users = UserProfile.objects.count()
    total_exams = Exam.objects.count()
    total_subscriptions = Subscription.objects.count()
    active_subscriptions = Subscription.objects.filter(active=True).count()
    total_payments = Payment.objects.count()
    
    # Get recent payments and contact messages
    recent_payments = Payment.objects.order_by('-created_at')[:5]
    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]

    # (Optional) Get some extra stats, e.g., questions per exam:
    exams_with_question_counts = Exam.objects.annotate(question_count=Count('questions')).order_by('-created_at')[:5]

    if request.method == 'POST':
        form = ScheduledExamForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Exam scheduled successfully!")
            return redirect('admin_dashboard')
    else:
        form = ScheduledExamForm()

    # Fetch exams
    scheduled_exams = ScheduledExam.objects.all().order_by('-upload_time')
    context = {
        'total_users': total_users,
        'total_exams': total_exams,
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'total_payments': total_payments,
        'recent_payments': recent_payments,
        'recent_messages': recent_messages,
        'exams_with_question_counts': exams_with_question_counts,
        'current_time': now(),
        'form': form,
        'scheduled_exams': scheduled_exams,
        
    }
    
    return render(request, 'admin_dashboard.html', context)
