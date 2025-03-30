from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from django.utils.timezone import now
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import *
from django.shortcuts import get_object_or_404
from .forms import *
import uuid
from .momo_utils import *
from .utils import *
from django.views.decorators.csrf import csrf_exempt
import json
import base64
from .decorators import * 
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_backends
from django.db.models import Q
from .authentication import EmailOrPhoneBackend  # Import the custom backend
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse
from apscheduler.schedulers.background import BackgroundScheduler
from django.views import View
from django.views.decorators.http import require_POST
from datetime import timedelta

# ---------------------

# Home View
def home(request):
    exams = Exam.objects.all()
    context = {
        'exams': exams,
    }
    return render(request, 'home.html', context)


class SubscriptionRequiredView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_subscribed:
            return redirect('subscription')
        return super().dispatch(request, *args, **kwargs)

@login_required
def exam_detail(request, pk):
    exam_obj = get_object_or_404(Exam, pk=pk)
    if not request.user.is_authenticated or not request.user.is_subscribed:
        messages.warning(request, "Your subscription has expired. Please subscribe to continue.")
        return redirect('subscription')
    return render(request, 'exam_detail.html', {'exam': exam_obj})


def exam_schedule_view(request):
    selected_time = request.GET.get('time')
    try:
        hour, minute = map(int, selected_time.split(':'))
        if not (6 <= hour <= 21):
            raise ValueError("Time not within allowed range")
    except (ValueError, AttributeError):
        messages.error(request, "Invalid time provided.")
        return redirect('error_page')

    is_available = check_exam_availability(hour)
    context = {
        'selected_time': f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}",
        'is_available': is_available
    }
    return render(request, 'exam_schedule.html', context)


# @login_required(login_url='login')
# def exams_list(request):
#     exams = Exam.objects.all()
#     return render(request, 'exams_list.html', {'exams': exams})

def scheduled_hours(request):
    now = timezone.localtime(timezone.now())
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    exams_scheduled = ScheduledExam.objects.filter(
        scheduled_datetime__range=(start_of_day, end_of_day)
    )
    
    
    
    context = {
        'exams_scheduled': exams_scheduled,
        'start_of_day': start_of_day,
        'end_of_day': end_of_day,
        'now': now,
    }

    return render(request, 'scheduled_hours.html', context)

def exam_timer(request, exam_id):
    try:
        scheduled_exam = ScheduledExam.objects.get(exam_id=exam_id)
        time_remaining = (scheduled_exam.scheduled_datetime - timezone.now()).total_seconds()
        return JsonResponse({'time_remaining': max(time_remaining, 0)})
    except ScheduledExam.DoesNotExist:
        return JsonResponse({'error': 'Exam not found'}, status=404)

@login_required(login_url='login')
def exams_by_title(request, exam_title):
    titled_exams = Exam.objects.filter(title=exam_title)
    counted_exams = titled_exams.count()
    context = {
        'exam_title' : exam_title,
        'titled_exams' : titled_exams,
        'counted_exams' : counted_exams,
    }    
    return render(request, "exams.html", context )
# ---------------------
# Exam / Question Views
# ---------------------


@login_required(login_url='login')
@subscription_required
def exam(request, exam_id, question_number):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = list(exam.questions.all())
    total_questions = len(questions)

    user_exam, created = UserExam.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={'score': 0, 'completed_at': None, 'started_at': timezone.now()}
    )

    if user_exam.completed_at:
        return redirect('retake_exam', exam_id=exam_id)

    if question_number < 1 or question_number > total_questions:
        messages.error(request, "Invalid question number.")
        return redirect('exam', exam_id=exam_id, question_number=1)

    current_question = questions[question_number - 1]

    exam_end_time = (user_exam.started_at + timedelta(minutes=exam.duration)).timestamp()

    if 'answers' not in request.session:
        request.session['answers'] = {}

    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        if user_answer:
            request.session['answers'][str(current_question.id)] = user_answer
            request.session.modified = True

        if 'next' in request.POST and question_number < total_questions:
            return redirect('exam', exam_id=exam_id, question_number=question_number + 1)
        elif 'previous' in request.POST and question_number > 1:
            return redirect('exam', exam_id=exam_id, question_number=question_number - 1)
        elif 'submit' in request.POST:
            score = 0
            for question in questions:
                correct_choice = question.correct_choice
                user_choice = request.session['answers'].get(str(question.id))
                if user_choice and int(user_choice) == correct_choice:
                    score += 1
                UserExamAnswer.objects.update_or_create(
                    user_exam=user_exam,
                    question=question,
                    defaults={'selected_choice_number': user_choice}
                )

            user_exam.score = score
            user_exam.completed_at = timezone.now()
            try:
                user_exam.save()
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('subscription')

            request.session.pop('answers', None)
            messages.success(request, f"Exam submitted! Your score: {score}/{total_questions}.")
            return redirect('exam_results', user_exam_id=user_exam.id)

    choices = []
    for i in range(1, 5):
        choice_text = getattr(current_question, f'choice{i}_text', None)
        choice_sign = getattr(current_question, f'choice{i}_sign', None)
        if choice_text:
            choices.append({'type': 'text', 'content': choice_text, 'id': i})
        elif choice_sign:
            choices.append({'type': 'image', 'content': choice_sign.image_url, 'id': i})

    context = {
        'exam': exam,
        'question': current_question,
        'question_number': question_number,
        'total_questions': total_questions,
        'choices': choices,
        'exam_end_time': exam_end_time,
        'exam_duration': exam.duration * 60,
        'user_exam': user_exam,
    }
    return render(request, 'exam.html', context)


@login_required(login_url='login')
def exam_results(request, user_exam_id):
    user_exam = get_object_or_404(UserExam, id=user_exam_id, user=request.user)
    answers = UserExamAnswer.objects.filter(user_exam=user_exam).select_related('question')

    context = {
        'user_exam': user_exam,
        'answers': answers,
        'total_questions': user_exam.exam.questions.count(),
        'score': user_exam.score,
    }
    return render(request, 'exam_results.html', context)

@login_required(login_url='login')
@subscription_required
def retake_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    user_exam = get_object_or_404(UserExam, exam=exam, user=request.user)

    if not user_exam.completed_at:
        return redirect('exam', exam_id=exam_id, question_number=1)

    if request.method == 'POST':
        user_exam.started_at = timezone.now()
        user_exam.completed_at = None
        user_exam.score = 0
        user_exam.save()

        if 'answers' in request.session:
            del request.session['answers']

        messages.info(request, "Your exam has been reset. Good luck!")
        return redirect('exam', exam_id=exam_id, question_number=1)

    context = {
        'exam': exam,
        'user_exam': user_exam,
    }
    return render(request, 'confirm_retake_exam.html', context)

# ---------------------
# Contact / Registration / Login Views
# ---------------------

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        ContactMessage.objects.create(name=name, email=email, message=message_text)
        messages.success(request, "Your message has been sent successfully!")
        return redirect('contact')
    return render(request, 'contact.html')


@redirect_authenticated_users
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password1"])
            user.otp_verified = True  # Mark active initially; may change if OTP is needed.
            user.save()

            if form.cleaned_data.get("email"):
                user.otp_verified = False
                user.send_otp_email()
                messages.success(request, 'OTP sent to your email. Verify your account.')
                return redirect('verify_otp', user_id=user.id)
            else:
                messages.success(request, 'Guhanga konti byagenze neza. Ushobora kwinjira.')
                return redirect("login")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    # messages.error(request, f"{field.capitalize()}: {error}")
                    messages.error(request, f"!!! 🙇🏼‍♂️ {error}")
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@redirect_authenticated_users
def verify_otp(request, user_id):
    # Fetch the UserProfile instance
    user_profile = get_object_or_404(UserProfile, id=user_id)
    if request.method == 'POST':
        otp = request.POST.get('otp')
        if user_profile.verify_otp(otp):
            user_profile.otp_verified = True
            user_profile.save()
            authenticated_user = authenticate(
                request,
                username=user_profile.phone_number or user_profile.email,
                password=user_profile.password  # Ensure the correct password is stored
            )


            if user_profile.phone_number == "":
                    user_profile.phone_number = None
                    user_profile.save(update_fields=["phone_number"])

            backend = get_backends()[0]
            user_profile.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user_profile)
            
            # Keep session active
            update_session_auth_hash(request, user_profile)

            messages.success(request, 'Account verified successfully. Welcome!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    return render(request, 'registration/verify_otp.html', {'user': user_profile})


@redirect_authenticated_users
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # Fetch user by email or phone number
             # Normalize phone number if needed
            if "@" not in username:  
                username = EmailOrPhoneBackend().normalize_phone_number(username)

            # Fetch user by email or phone number
            user = UserProfile.objects.filter(Q(phone_number=username) | Q(email=username)).first()
            if user:
                # Ensure phone_number is set to None if empty
                if user.phone_number == "":
                    user.phone_number = None
                    user.save(update_fields=["phone_number"])
                
                if user.email and not user.otp_verified:
                    messages.error(request, "Please banza wuzuze kode yoherejwe yemeza ko email ari yawe.")
                    return redirect("verify_otp", user_id=user.id)
                authenticated_user = authenticate(request, username=username, password=password)
                if authenticated_user:
                    login(request, authenticated_user)
                    messages.success(request, "Kwinjira bikozwe neza cyane! Welcome back.")
                    return redirect("home")
                else:
                    messages.error(request, "Ijambobanga ritariryo, ongera ugerageze.")
            else:
                messages.error(request, "Iyi konti ntago ibaho, Gusa wayihanga.")

        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = LoginForm()
    return render(request, "registration/login.html", {"form": form})


@require_POST
@login_required(login_url='login')
def user_logout(request):
    logout(request)
    messages.success(request, "Gusohoka bigenze neza.")
    return redirect('home')


# ---------------------
@login_required(login_url='login')
def payment(request):
    plans = Plan.PLAN_CHOICES
    context = {
        'plans': plans,
    }
    return render(request, 'payment.html', context)
# ---------------------
# Subscription and Payment Views
# ---------------------

@login_required(login_url='login')
def subscription_view(request):
    plans = Plan.PLAN_CHOICES
    # sub = request.user.subscription and request.user.subscription.expires_at > timezone.now().date()

    subscription, created = Subscription.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        plan_choice = request.POST.get('plan')
        phone_number = request.POST.get('phone_number')

        if plan_choice not in dict(plans):
            messages.error(request, "Ikiciro kitaricyo.")
            return redirect('subscription')

        try:
            selected_plan = Plan.objects.get(plan=plan_choice)
        except Plan.DoesNotExist:
            messages.error(request, "Ikiciro wahisempo ntikibaho.")
            return redirect('subscription')

        # This function should return (price, duration_days) for the selected plan.
        price, duration_days = set_price_and_duration(plan_choice)  # Ensure this helper exists.

        payment_response, transaction_id = request_momo_payment(phone_number, price)
        if "error" in payment_response:
            messages.error(request, payment_response["error"])
            return redirect('subscription')

        # Save transaction details
        subscription.plan = selected_plan  # ✅ Assign the Plan instance
        subscription.price = price
        subscription.duration_days = duration_days
        subscription.phone_number = phone_number
        subscription.transaction_id = transaction_id
        subscription.save()


        messages.info(request, "Kwemeza ubwishyu byoherejwe. reba kuri telefone wemeze.")
        return redirect('momo_payment_status', transaction_id=transaction_id)

    context = {
        'subscription': subscription,
        'plans': plans,
        # 'sub': sub
    }
    return render(request, 'subscription.html', context)


def momo_payment(request):
    
    phone_number = request.GET.get("phone")
    amount = request.GET.get("amount")
    if not phone_number or not amount:
        return JsonResponse({"error": "Telefone n'igiciro birakenewe"}, status=400)

    payment_response, transaction_id = request_momo_payment(phone_number, amount)
    if "error" in payment_response:
        return JsonResponse(payment_response, status=500)
    return JsonResponse({"message": "Payment request sent", "transaction_id": transaction_id})


def momo_payment_status(request, transaction_id):
    if not transaction_id or transaction_id == "None":
        return JsonResponse({"error": "Invalid transaction ID"}, status=400)
    status = check_payment_status(transaction_id)
    return JsonResponse(status)


# ---------------------
#404 Error Page
def custom_page_not_found(request, exception):
    # You can add extra context if needed
    context = {}
    return render(request, '404.html', context, status=404)

class PrivacyPolicyView(View):
    def get(self, request):
        return render(request, 'privacy_policy.html')

# Add this to your existing views
def base_view(request):
    context = {
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'base.html', context)