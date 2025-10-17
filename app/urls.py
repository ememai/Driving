from django.urls import path
from . import views, user_profile_view
from .user_profile_view import profile_view
from .views import *
from .decorators import subscription_required
from .api import get_questions_for_exam_type
from django.core.exceptions import PermissionDenied
from django.contrib.auth import views as auth_views
from app.forms import CustomSetPasswordForm

urlpatterns = [
    # path('admin/api/questions/', get_questions_for_exam_type),
    path('check-unverified/', views.check_unverified_subscription, name='check_unverified'),

    path("ahabanza/", views.home, name='ahabanza'),
    path('isomo/<slug:slug>/', views.course_detail, name='course_detail'),
    path("", views.home, name='home'),
    path('isomo/stream/<int:course_id>/', views.secure_stream, name='secure_stream'),
    path('isomo/download/<int:course_id>/', views.secure_download, name='secure_download'),
    path('amasomo/', views.courses, name='courses'),
    path("ibibazo-byo-mubwoko-/<str:exam_type>/", exams_by_type, name='exams'),
    path('exam-detail/<int:pk>/', subscription_required(views.exam_detail), name='exam_detail'),

    path('create-exam/', create_exam_page, name='create_exam'),
    path('undo-last-exam/', undo_last_exam_action, name='undo_last_exam_action'),
    path('schedule-exams/', schedule_recent_exams, name='auto_schedule_exams'),
    path('exam/<int:exam_id>/<int:question_number>/', subscription_required(views.exam), name='exam'),
    path('exam/<int:exam_id>/ajax/<int:question_number>/', views.ajax_question, name='ajax_question'),

    path('exam-results/<int:user_exam_id>/', views.exam_results, name='exam_results'),

    path('exam/<int:exam_id>/retake/', views.retake_exam, name='retake_exam'),
    path('ibizamini-byicyumweru/', views.weekly_exams, name='weekly_exams'),

    path('check-exam-status/<int:exam_id>/', check_exam_status, name='check_exam_status'),
    path('exam-timer/<int:exam_id>/', subscription_required(views.exam_timer), name='exam_timer'),
    path('exam/schedule/', subscription_required(views.exam_schedule_view), name='exam_schedule'),

    # path('scheduled_hours/', views.scheduled_hours, name='scheduled_hours'),


    #subscription and payment
    path('subscription/', views.subscription_status, name='subscription'),
    path('subscription/activate', views.activate_subscription_view, name='activate_subscription'),
    path('pay/', views.payment, name='payment'),
    
    path('payment/confirm/', views.payment_confirm, name='payment_confirm'),
    # path("pay/", momo_payment, name="momo_payment"),
    # path("pay/status/<str:transaction_id>/", momo_payment_status, name="momo_payment_status"),
    
    path('contact/', views.contact, name='contact'),
    path("ajax/check-unique/", views.check_unique_field, name="check_unique_field"),
    #authentications
    path('register/', register_view, name='register'),
    path('whatsapp-consent/', views.whatsapp_consent, name='whatsapp_consent'),
    path('verify-otp/<int:user_id>/', verify_otp, name='verify_otp'),
    path('resend-otp/<int:user_id>/', views.resend_otp, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),  
    
    #user profile
    path('profile/', profile_view, name='profile'),
    path('mark-notification-read/', user_profile_view.mark_notification_read, name='mark_notification_read'),
    
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    
    path('hindura-password/', views.password_reset, name='password_reset'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
]