from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils.timezone import now
from django.contrib import messages
from .models import Exam, ScheduledExam
from .forms import ScheduledExamForm
from .tasks import publish_scheduled_exams

@staff_member_required
def admin_dashboard(request):
    """
    Displays key statistics and allows scheduling of exams.
    """
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # AJAX request
        data = {
            'total_exams': Exam.objects.count(),
            'scheduled_exams': ScheduledExam.objects.count(),
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
            messages.success(request, "Exam scheduled successfully!")
            return JsonResponse({'message': 'Exam scheduled successfully!'}, status=200)
        return JsonResponse({'error': form.errors}, status=400)
