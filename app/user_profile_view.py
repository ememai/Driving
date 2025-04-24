from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import *
from django.template.loader import render_to_string


@login_required
def profile_view(request):
    """
    Render the user profile page with subscription details,
    exam history, recent activity, and notifications.
    """
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by('-timestamp')
    exam_history = user.userexam_set.all().order_by('-completed_at')
    pass_exams = UserExam.objects.with_percent_score().filter(user=user, percent_score_db__gte=60)
    fail_exams = UserExam.objects.with_percent_score().filter(user=user, percent_score_db__lt=60)

    activities = user.useractivity_set.all().order_by('-timestamp')[:10]  # last 10 activities

    context = {
        'user': user,
        'notifications': notifications,
        'exam_history': exam_history,
        'activities': activities,
        'pass_exams': pass_exams,
        'fail_exams': fail_exams
    }
    return render(request, 'profile.html', context)

@login_required
def load_more_exams(request):
    exam_type = request.GET.get('type')
    offset = int(request.GET.get('offset', 0))

    if exam_type == "exams":
        queryset = request.user.userexam_set.all().order_by('-completed_at')
    elif exam_type == "passed":
        queryset = UserExam.objects.with_percent_score().filter(user=request.user, percent_score_db__gte=60)
    elif exam_type == "failed":
        queryset = UserExam.objects.with_percent_score().filter(user=request.user, percent_score_db__lt=60)
    else:
        return JsonResponse({"error": "Invalid type"}, status=400)

    exams = queryset[offset:offset + 5]
    html = render_to_string("partials/exam_card.html", {"exams": exams})
    has_more = queryset.count() > offset + 5

    return JsonResponse({"html": html, "has_more": has_more})


@login_required 
def mark_notification_read(request):
    """
    AJAX endpoint to mark a notification as read.
    Expects a POST with 'notification_id'.
    """
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
