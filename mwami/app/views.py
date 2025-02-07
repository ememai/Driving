from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
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
from .authentication import EmailOrPhoneBackend  # Adjust if needed




# Home View
def home(request):
    return render(request, 'home.html')


@login_required(login_url='login')
def exams_list(request):
    exams = Exam.objects.all()
    return render(request, 'exams_list.html', {'exams': exams})


@login_required(login_url='login')
def exam(request, exam_id, question_number):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = list(exam.questions.all().select_related('correct_choice'))
    total_questions = len(questions)

    # Validate question number
    if question_number < 1 or question_number > total_questions:
        messages.error(request, "Invalid question number.")
        return redirect('exam', exam_id=exam_id, question_number=1)

    current_question = questions[question_number - 1]

    # Ensure UserExam record
    user_exam, created = UserExam.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={'score': 0, 'completed_at': None}
    )

    # Initialize session if not set
    if 'answers' not in request.session:
        request.session['answers'] = {}

    if request.method == 'POST':
        user_answer = request.POST.get('answer')

        if user_answer:
            request.session['answers'][str(current_question.id)] = user_answer
            request.session.modified = True  # Mark session as modified

        # Navigation logic
        if 'next' in request.POST and question_number < total_questions:
            return redirect('exam', exam_id=exam_id, question_number=question_number + 1)
        elif 'previous' in request.POST and question_number > 1:
            return redirect('exam', exam_id=exam_id, question_number=question_number - 1)
        elif 'submit' in request.POST:
            # Calculate final score
            score = 0
            for question in questions:
                correct_answer = question.correct_choice
                user_answer = request.session['answers'].get(str(question.id))

                if user_answer and user_answer == str(correct_answer.id):
                    score += 1

                # Save user response in the database
                selected_choice = Choice.objects.filter(id=user_answer).first()
                UserExamAnswer.objects.update_or_create(
                    user_exam=user_exam,
                    question=question,
                    defaults={'selected_choice': selected_choice}
                )

            # Save UserExam record
            user_exam.score = score
            user_exam.completed_at = now()
            user_exam.save()

            # Clear session
            request.session.pop('answers', None)

            messages.success(request, f"Exam submitted! Your score: {score}/{total_questions}.")
            return redirect('exam_results', user_exam_id=user_exam.id)

    return render(request, 'exam.html', {
        'exam': exam,
        'question': current_question,
        'question_number': question_number,
        'total_questions': total_questions,
        'questions': questions,
    })


@login_required(login_url='login')
def exam_results(request, user_exam_id):
    user_exam = get_object_or_404(UserExam, id=user_exam_id, user=request.user)
    answers = UserExamAnswer.objects.filter(user_exam=user_exam).select_related('question', 'selected_choice')

    question_choices = {
        answer.question.id: list(answer.question.choices.all()) for answer in answers
    }

    return render(request, 'exam_results.html', {
        'user_exam': user_exam,
        'answers': answers,
        'question_choices': question_choices
    })

# Contact View

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        ContactMessage.objects.create(name=name, email=email, message=message)
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
            user.active = True  # User remains inactive until OTP is verified
            user.save()

            if 'email' in form.cleaned_data and form.cleaned_data["email"]:
                user.active = False
                user.send_otp_email()  # Send OTP
                messages.success(request, 'OTP sent to your email. Verify your account.')
                return redirect('verify_otp', user_id=user.id)
            else:
                messages.success(request, 'Account created successfully. Please login.')
                return redirect("login")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


@redirect_authenticated_users
def verify_otp(request, user_id):
    # Fetch the UserProfile instance
    user_profile = get_object_or_404(UserProfile, id=user_id)

    if request.method == 'POST':
        otp = request.POST.get('otp')
        if user_profile.verify_otp(otp):  # Verify the OTP
            user_profile.active = True
            user_profile.save()

            # Authenticate the user (this sets the backend attribute)
            authenticated_user = authenticate(
                request,
                username=user_profile.phone_number or user_profile.email,
                password=user_profile.password  # Ensure the correct password is stored
            )

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
                
                if not user.active:
                    messages.error(request, "Please verify your OTP before logging in.")
                    return redirect("verify_otp", user_id=user.id)


                # Authenticate user
                authenticated_user = authenticate(request, username=username, password=password)

                if authenticated_user:
                    login(request, authenticated_user)
                    messages.success(request, "Login successful! Welcome back.")
                    return redirect("home")
                else:
                    messages.error(request, "Invalid password. Please try again.")
            else:
                messages.error(request, "User not found. Please register first.")

        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = LoginForm()

    return render(request, "registration/login.html", {"form": form})


# @redirect_authenticated_users
# def login_view(request):
    
#     if request.method == "POST":
#         form = LoginForm(request.POST)
#         if form.is_valid():
#             username = form.cleaned_data["username"]
#             password = form.cleaned_data["password"]

#             # # Normalize phone number before authentication
#             # if "@" not in username:
#             #     username = EmailOrPhoneBackend().normalize_phone_number(username)
#             if user.phone_number == "":
#                 user.phone_number = None
#                 user.save(update_fields=["phone_number"])



#             user = UserProfile.objects.filter(email=username).first() or \
#                    UserProfile.objects.filter(phone_number=username).first()

#             if user:
#                 authenticated_user = authenticate(request, username=username, password=password)

#                 if authenticated_user:
#                     login(request, authenticated_user)
#                     messages.success(request, "Login successful! Welcome back.")
#                     return redirect("home")
#                 else:
#                     messages.error(request, "Invalid password. Please try again.")
#             else:
#                 messages.error(request, "User not found. Please register first.")

#         for field, errors in form.errors.items():
#             for error in errors:
#                 messages.error(request, f"{field.capitalize()}: {error}")

#     else:
#         form = LoginForm()

#     return render(request, "registration/login.html", {"form": form})


def user_logout(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')



@login_required(login_url='login')
def subscription_view(request):
    """Allow users to subscribe via MTN MoMo."""
    plans = Plan.PLAN_CHOICES  # This is a list of tuples (value, label)
    subscription, created = Subscription.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        plan = request.POST.get('plan')
        phone_number = request.POST.get('phone_number')

        # Validate plan (Check only the plan values)
        if plan not in dict(plans):
            messages.error(request, "Invalid plan selected.")
            return redirect('subscription')

        # Get the Plan instance (case-insensitive lookup)
        selected_plan = Plan.objects.get(plan=plan)
        if not selected_plan:
            messages.error(request, "Selected plan does not exist.")
            return redirect('subscription')

        # Set price and duration
        price, duration_days = set_price_and_duration(plan)

        # Request payment
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

        messages.info(request, "Payment request sent. Complete payment on your phone.")
        return redirect('momo_payment_status', transaction_id=transaction_id)

    context = {
        'subscription': subscription,
        'plans': plans,
    }

    return render(request, 'subscription.html', context)



def momo_payment(request):
    """Handle MoMo payment requests."""
    phone_number = request.GET.get("phone")
    amount = request.GET.get("amount")

    if not phone_number or not amount:
        return JsonResponse({"error": "Phone number and amount are required"}, status=400)

    payment_response, transaction_id = request_momo_payment(phone_number, amount)

    if "error" in payment_response:
        return JsonResponse(payment_response, status=500)

    return JsonResponse({"message": "Payment request sent", "transaction_id": transaction_id})


def momo_payment_status(request, transaction_id):
    """Check MoMo payment status."""
    if not transaction_id or transaction_id == "None":
        return JsonResponse({"error": "Invalid transaction ID"}, status=400)

    status = check_payment_status(transaction_id)
    return JsonResponse(status)


    