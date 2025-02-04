from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import *
from django.shortcuts import get_object_or_404
from .forms import SubscriptionForm
import uuid
from .momo_utils import get_access_token, request_payment, check_payment_status
from django.views.decorators.csrf import csrf_exempt
import json


# Home View
def home(request):
    context = {}
    return render(request, 'home.html', context)

@login_required(login_url='login')
def exams_list(request):
    exams = Exam.objects.all()
    context = {'exams': exams}
    return render(request, 'exams_list.html', context)

# Exam View
@login_required(login_url='login')
def exam(request, exam_id, question_number):
   #exam = Exam.objects.get(id=exam_id)
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        messages.error(request, "Exam not found.")
        return redirect('home')

    questions = list(exam.questions.all())
    total_questions = len(questions)

    # Validate question number
    if question_number < 1 or question_number > total_questions:
        messages.error(request, "Invalid question number.")
        return redirect('exam', exam_id=exam_id, question_number=1)

    # Get current question
    current_question = questions[question_number - 1]

    user_exam, created = UserExam.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={'score': 0, 'completed_at': None}
    )


    # Initialize answers in session if not present
    if 'answers' not in request.session:
        request.session['answers'] = {}

    # Save user's answer for the current question
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        if user_answer:
            request.session['answers'][str(current_question.id)] = user_answer
            request.session.modified = True

        # Navigate to the next or previous question
        if 'next' in request.POST and question_number < total_questions:
            return redirect('exam', exam_id=exam_id, question_number=question_number + 1)
        elif 'previous' in request.POST and question_number > 1:
            return redirect('exam', exam_id=exam_id, question_number=question_number - 1)
        elif 'submit' in request.POST:
            # Calculate score
            score = 0
            for question in questions:
                correct_answer = question.correct_choice
                user_answer = request.session['answers'].get(str(question.id))
                if user_answer == correct_answer:
                    score += 1
                
                UserExamAnswer.objects.update_or_create(
                user_exam=user_exam,
                question=question,
                defaults={'selected_choice': user_answer}
                )                

            # Save UserExam record
            user_exam.score = score
            user_exam.completed_at = now()
            user_exam.save()

            try:
                del request.session['answers']
            except KeyError:
                pass
  # Clear session answers
            return redirect('exam_results', user_exam_id=user_exam.id)

            messages.success(request, f"Exam submitted! Your score: {score}/{total_questions}.")
    
    context = {
        'exam': exam,
        'question': current_question,
        'question_number': question_number,
        'total_questions': total_questions,
    }

    return render(request, 'exam.html', context)

# Results View
@login_required(login_url='login')
def exam_results(request, user_exam_id):
    user_exam = get_object_or_404(UserExam, id=user_exam_id, user=request.user)
    answers = UserExamAnswer.objects.filter(user_exam=user_exam).select_related('question')
    question_choices = {
        answer.question.id: {
            'choice1': answer.question.choice1,
            'choice2': answer.question.choice2,
            'choice3': answer.question.choice3,
            'choice4': answer.question.choice4,
        }
        for answer in answers
    }
    context = {'user_exam': user_exam, 'answers': answers , 'question_choices': question_choices}
    return render(request, 'exam_results.html', context)


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

# Login View
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('home')
        else:
            messages.error(request, "!!! imyirondoro itariyo , ongera ugerageze")
    return render(request, 'registration/login.html')

# Logout View
def user_logout(request):
    logout(request)
    messages.warning(request, "You have been logged out.")
    return redirect('home')

# Registration View
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            Subscription.objects.create(user=user, active=False)
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')
    return render(request, 'registration/register.html')


@login_required(login_url='login')
def subscription_view(request):
   # """Allow users to subscribe via MTN MoMo."""
    subscription, created = Subscription.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        plan = request.POST.get('plan')
        if plan == 'monthly':
            price = 10
            duration_days = 30
        elif plan == 'yearly':
            price = 100
            duration_days = 365
        else:
            messages.error(request, "Invalid plan selected.")
            return redirect('subscription')

        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())
        phone_number = request.POST.get('phone_number')  # User's phone number

        # Request payment
        payment_requested = request_payment(phone_number, price, transaction_id, callback_url="your_callback_url")

        if payment_requested:
            messages.info(request, "Payment request sent. Complete payment on your phone.")
            # Save transaction details (optional)
            # Redirect to check payment status
            return redirect('check_payment', transaction_id=transaction_id, duration_days=duration_days)
        else:
            messages.error(request, "Payment request failed. Try again.")
            return redirect('subscription')

    return render(request, 'subscription.html', {'subscription': subscription})


#initializing the subscription form
@login_required(login_url='login')
def initiate_payment(request):
    phone_number = request.POST.get("phone_number")
    amount = request.POST.get("amount")
    transaction_id = generate_transaction_id()
    callback_url = "https://yourdomain.com/momo/callback/"  # Replace with your callback URL

    try:
        payment_initiated = request_payment(phone_number, amount, transaction_id, callback_url)
        if payment_initiated:
            return JsonResponse({"success": True, "message": "Payment initiated.", "transaction_id": transaction_id})
        return JsonResponse({"success": False, "message": "Failed to initiate payment."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})

# Momo Callback View
@csrf_exempt
def momo_callback(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Callback Data:", data)
            
            transaction_id = data.get("externalId")
            status = data.get("status")

            # Update payment record
            payment = Payment.objects.get(transaction_id=transaction_id)
            payment.status = status
            payment.save()

            # Send response
            return JsonResponse({"status": "received"})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)
        except Payment.DoesNotExist:
            return JsonResponse({"error": "Payment record not found."}, status=404)
    return JsonResponse({"error": "Invalid request."}, status=400)

# Check Payment View
def check_payment(request, transaction_id, duration_days):
   # """Check payment status and activate subscription."""
    status = check_payment_status(transaction_id)
    try:
        duration_days = int(duration_days)
    except ValueError:
        messages.error(request, "Invalid subscription duration.")
    return redirect('subscription')
    if status.get("status") == "SUCCESSFUL":
        subscription = Subscription.objects.get(user=request.user)
        subscription.activate(duration_days=duration_days)
        messages.success(request, "Payment successful! Subscription activated.")
        return redirect('dashboard')
    elif status.get("status") == "FAILED":
        messages.error(request, "Payment failed. Try again.")
    else:
        messages.info(request, "Payment is still pending. Please wait.")
    return redirect('subscription')