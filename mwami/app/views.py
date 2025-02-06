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


def register_view(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.active = False  # User remains inactive until OTP is verified
            user.save()

            if 'email' in form.cleaned_data:  # Check if email is provided
                user.send_otp_email()  # Send OTP
                messages.success(request, 'OTP sent to your email. Verify your account.')
                return redirect('verify_otp', user_id=user.id)
            else:
                return redirect("home")
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})

def verify_otp(request, user_id):
    """Handle OTP verification"""
    user = get_object_or_404(UserProfile, id=user_id)
    
    if request.method == 'POST':
        otp = request.POST.get('otp')
        if user.verify_otp(otp):
            user.active = True
            user.save()
            login(request, user)  # Log in the user after verification
            messages.success(request, 'Account verified successfully.')
            return redirect('home')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'registration/verify_otp.html', {'user': user})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data["phone_number"]
            password = form.cleaned_data["password"]
            user = authenticate(request, phone_number=phone_number, password=password)

            if user:
                login(request, user)
                return redirect("home")
            else:
                form.add_error(None, "Invalid login credentials.")
    else:
        form = LoginForm()
    return render(request, "registration/login.html", {"form": form})


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










# def subscription_view(request):
#     """Allow users to subscribe via MTN MoMo."""
#     subscription, created = Subscription.objects.get_or_create(user=request.user)

#     if request.method == 'POST':
#         plan = request.POST.get('plan')
#         phone_number = request.POST.get('phone_number')

#         # Validate plan
#         if plan not in ['monthly', 'yearly']:
#             messages.error(request, "Invalid plan selected.")
#             return redirect('subscription')

#         # Set price and duration
#         price = 10 if plan == 'monthly' else 100
#         duration_days = 30 if plan == 'monthly' else 365

#         # Validate and format phone number
#         formatted_phone = format_phone_number(phone_number)
#         if not formatted_phone:
#             messages.error(request, "Invalid phone number. Please enter a valid number.")
#             return redirect('subscription')

#         # Generate transaction ID
#         transaction_id = str(uuid.uuid4())

#         # Request payment
#         try:
#             payment_requested, transaction_id = request_momo_payment(
#                 phone_number=formatted_phone,
#                 amount=price,                 
#             )
#         except Exception as e:
#             messages.error(request, f"Error processing payment: {str(e)}")
#             return redirect('subscription')

#         if payment_requested:
#             # Save transaction details
#             subscription.plan = plan
#             subscription.price = price
#             subscription.duration_days = duration_days
#             subscription.phone_number = formatted_phone
#             subscription.transaction_id = transaction_id
#             subscription.save()

#             messages.info(request, "Payment request sent. Complete payment on your phone.")
#             return redirect('momo_payment_status', transaction_id=transaction_id)
#         else:
#             messages.error(request, "Payment request failed. Please try again.")
#             return redirect('subscription')

#     return render(request, 'subscription.html', {'subscription': subscription})


# def momo_payment(request):
#     phone_number = request.GET.get("phone")
#     amount = request.GET.get("amount")

#     if not phone_number or not amount:
#         return JsonResponse({"error": "Phone number and amount are required"}, status=400)

#     status_code, transaction_id = request_momo_payment(phone_number, amount)

#     if status_code == 202:
#         return JsonResponse({"message": "Payment request sent", "transaction_id": transaction_id})
#     return JsonResponse({"error": "Failed to initiate payment"}, status=500)

# def momo_payment_status(request, transaction_id):
#     if not transaction_id or transaction_id == "None":
#         return JsonResponse({"error": "Invalid transaction ID"}, status=400)

#     status = check_payment_status(transaction_id)
#     return JsonResponse(status)


