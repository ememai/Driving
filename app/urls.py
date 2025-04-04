from django.urls import path
from . import views, user_profile_view
from .views import *
from .decorators import subscription_required
from .api import get_questions_for_exam_type
from django.core.exceptions import PermissionDenied


urlpatterns = [
    # path('admin/api/questions/', get_questions_for_exam_type),

    path("ahabanza/", views.home, name='ahabanza'),
    path("", views.home, name='home'),
    path("ibibazo-byo-mubwoko-/<str:exam_type>/", exams_by_type, name='exams'),
    path('exam-detail/<int:pk>/', subscription_required(views.exam_detail), name='exam_detail'),

     path('create/', views.create_exam, name='create_exam'),
    path('exam/<int:exam_id>/<int:question_number>/', subscription_required(views.exam), name='exam'),
    path('exam-results/<int:user_exam_id>/', subscription_required(views.exam_results), name='exam_results'),

    path('exam/<int:exam_id>/retake/', views.retake_exam, name='retake_exam'),


    path('check-exam-status/<int:exam_id>/', check_exam_status, name='check_exam_status'),
    path('exam-timer/<int:exam_id>/', subscription_required(views.exam_timer), name='exam_timer'),
    path('exam/schedule/', subscription_required(views.exam_schedule_view), name='exam_schedule'),

    # path('scheduled_hours/', views.scheduled_hours, name='scheduled_hours'),


    #subscription and payment
    path('subscription/', views.payment, name='subscription'),
    # path("pay/", momo_payment, name="momo_payment"),
    # path("pay/status/<str:transaction_id>/", momo_payment_status, name="momo_payment_status"),
    
    path('contact/', views.contact, name='contact'),

    #authentications
    path('register/', register_view, name='register'),
    path('verify-otp/<int:user_id>/', verify_otp, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),  
    
    #user profile
    path('profile/', user_profile_view.profile_view, name='profile'),
    path('mark-notification-read/', user_profile_view.mark_notification_read, name='mark_notification_read'),
    
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
]