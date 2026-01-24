# dashboard/urls.py
from django.urls import path
from .views import *

# app_name = 'dashboard'

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('staff-login/', StaffLoginView.as_view(), name='staff_login'),
    path('schedule-exam/', schedule_exam, name='schedule_exam'),
    path('schedule-exam/<int:pk>/update/', scheduled_exam_update, name='scheduled_exam_update'),
    path('schedule-exam/<int:pk>/delete/', scheduled_exam_delete, name='scheduled_exam_delete'),
    path('create-subscription/', CreateSubscriptionView.as_view(), name='create_subscription'),
    path('subscription/<int:pk>/update/', subscription_update, name='subscription_update'), 
]
