from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Notification, UserExam, UserActivity

@login_required
def profile_view(request):
    """
    Render the user profile page with subscription details,
    exam history, recent activity, and notifications.
    """
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by('-timestamp')
    exam_history = user.userexam_set.all().order_by('-completed_at')
    activities = user.useractivity_set.all().order_by('-timestamp')[:10]  # last 10 activities

    context = {
        'user': user,
        'notifications': notifications,
        'exam_history': exam_history,
        'activities': activities,
    }
    return render(request, 'profile.html', context)

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
