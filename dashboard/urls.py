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
    path('subscriptions/', subscription_dashboard, name='admin_subscription_dashboard'),
    path('subscriptions/update-plans/', dashboard_update_plans, name='dashboard_update_plans'),
    path('subscriptions/<int:pk>/renew/', renew_subscription, name='dashboard_renew_subscription'),
    path('subscriptions/<int:pk>/end/', end_subscription, name='dashboard_end_subscription'),
    path('subscriptions/add-subscription/', dashboard_add_subscription, name='dashboard_add_subscription'),
    path('subscriptions/bulk-delete/', dashboard_bulk_delete, name='dashboard_bulk_delete'),
]
