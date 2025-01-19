from django.urls import path
from . import views
from .views import momo_callback

urlpatterns = [
    path('', views.home, name='home'),
    path('exams/', views.exams_list, name='exams'),
    path('exam/<int:exam_id>/', views.exam, {'question_number': 1}, name='exam'),
    path('exam/<int:exam_id>/<int:question_number>/', views.exam, name='exam'),
    path('exam-results/<int:user_exam_id>/', views.exam_results, name='exam_results'),
    path('subscription/', views.subscription_view, name='subscription'),
    path("momo/callback/", momo_callback, name="momo_callback"),
    path('contact/', views.contact, name='contact'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
]