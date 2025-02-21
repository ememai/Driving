
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from app.models import *
from .forms import ScheduledExamForm

# A helper test so that only staff (admin) users can access these views.
def staff_required(user):
    return user.is_staff

@login_required
@user_passes_test(staff_required)
def admin_dashboard(request):
    """
    Displays tables for Payments, Subscriptions, Users, and Scheduled Exams.
    """
    payments = Payment.objects.all()
    subscriptions = Subscription.objects.all()
    users = UserProfile.objects.all()
    scheduled_exams = ScheduledExam.objects.all()
    
    context = {
        'payments': payments,
        'subscriptions': subscriptions,
        'users': users,
        'scheduled_exams': scheduled_exams,
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
@user_passes_test(staff_required)
def schedule_exam(request):
    """
    Displays and processes the form to schedule a new exam.
    """
    if request.method == 'POST':
        form = ScheduledExamForm(request.POST)
        if form.is_valid():
            scheduled_exam = form.save()
            messages.success(request, f"Exam scheduled successfully for {scheduled_exam.scheduled_datetime}.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ScheduledExamForm()
    context = {
        'form': form,
    }
    return render(request, 'dashboard/schedule_exam.html', context)

@login_required
@user_passes_test(staff_required)
def scheduled_exam_update(request, pk):
    """
    Displays and processes the form to update an existing scheduled exam.
    """
    scheduled_exam = get_object_or_404(ScheduledExam, pk=pk)
    if request.method == 'POST':
        form = ScheduledExamForm(request.POST, instance=scheduled_exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Scheduled exam updated successfully.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ScheduledExamForm(instance=scheduled_exam)
    context = {'form': form, 'scheduled_exam': scheduled_exam}
    return render(request, 'dashboard/schedule_exam_update.html', context)

@login_required
@user_passes_test(staff_required)
def scheduled_exam_delete(request, pk):
    """
    Confirms and then deletes the selected scheduled exam.
    """
    scheduled_exam = get_object_or_404(ScheduledExam, pk=pk)
    if request.method == 'POST':
        scheduled_exam.delete()
        messages.success(request, "Scheduled exam deleted successfully.")
        return redirect('admin_dashboard')
    context = {'scheduled_exam': scheduled_exam}
    return render(request, 'dashboard/schedule_exam_delete.html', context)
