from django.urls import path
from . import views, admin_views
from .views import *

urlpatterns = [
    path('', views.home, name='home'),
    path('exams/', views.exams_list, name='exams'),
    path('exam/<int:exam_id>/', views.exam, {'question_number': 1}, name='exam'),

    path('exam/<int:exam_id>/<int:question_number>/', views.exam, name='exam'),
    path('exam-results/<int:user_exam_id>/', views.exam_results, name='exam_results'),

    #subscription and payment
    path('subscription/', views.subscription_view, name='subscription'),
    path("pay/", momo_payment, name="momo_payment"),
    path("pay/status/<str:transaction_id>/", momo_payment_status, name="momo_payment_status"),
    
    path('contact/', views.contact, name='contact'),

    #authentications
    path('register/', register_view, name='register'),
    path('verify-otp/<int:user_id>/', verify_otp, name='verify_otp'),
    path('login/', login_view, name='login'),
    path('logout/', user_logout, name='logout'),

    #admin views
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('schedule-exam/', admin_views.schedule_exam, name='schedule_exam'),

    
]