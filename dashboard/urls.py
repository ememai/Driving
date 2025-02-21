# dashboard/urls.py
from django.urls import path
from . import views

# app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('schedule-exam/', views.schedule_exam, name='schedule_exam'),
    path('schedule-exam/<int:pk>/update/', views.scheduled_exam_update, name='scheduled_exam_update'),
    path('schedule-exam/<int:pk>/delete/', views.scheduled_exam_delete, name='scheduled_exam_delete'),
]
