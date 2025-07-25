from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
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
from django.middleware.csrf import get_token
import json
import base64
from .decorators import * 
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_backends
from django.db.models import Q
from .authentication import EmailOrPhoneBackend  # Import the custom backend
from django.utils.timezone import now, localtime, make_aware
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse
from apscheduler.schedulers.background import BackgroundScheduler
from django.views import View
from django.views.decorators.http import require_POST, require_GET
from datetime import datetime, timedelta, time, date
import random
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.http import JsonResponse,FileResponse,Http404
from .scheduler import notify_admin
import mimetypes
import markdown
from wsgiref.util import FileWrapper

User = get_user_model()

@login_required(login_url='register')
def home(request):
    exam_types = ExamType.objects.filter(
        exam__isnull=False, exam__for_scheduling=False
    ).distinct().order_by('order')

    # Annotate each exam type with the count of non-scheduled exams
    exam_types = exam_types.annotate(
        actual_exam_count=Count('exam', filter=Q(exam__for_scheduling=False))
    )

    courses = Course.objects.all()
    query = request.GET.get('q')
    category = request.GET.get('category')

    if query:
        courses = courses.filter(title__icontains=query)

    if category:
        courses = courses.filter(category=category)

    context = {
        'exam_types': exam_types,
        'num': exam_types.count(),
        'courses': courses,
        'query': query or '',
        'selected_category': category or '',
        'categories': Course._meta.get_field('category').choices,
        
        }
    return render(request, 'home.html', context)

@login_required
@subscription_required
def secure_download(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        user = request.user

        # Authorization logic
        if user.is_subscribed and user.subscription.plan.plan.lower() in ['vip', 'weekly']:
            return FileResponse(course.course_file.open('rb'), as_attachment=True)
        else:
            raise PermissionError("Unauthorized download attempt.")

    except (Course.DoesNotExist, PermissionError):
        raise Http404("You do not have permission to access this file.")

@login_required
@subscription_required
def secure_stream(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        user = request.user

        if not course.course_file:
            raise Http404("No file found.")

        if user.is_subscribed and user.subscription.plan.plan.lower() in ['vip', 'weekly', 'daily']:
            mime_type, _ = mimetypes.guess_type(course.course_file.name)
            wrapper = FileWrapper(course.course_file.open('rb'))
            return FileResponse(wrapper, content_type=mime_type or 'application/octet-stream')
        else:
            raise PermissionError("Unauthorized")
    except (Course.DoesNotExist, PermissionError):
        raise Http404("Access denied.")


@login_required(login_url='login')
@subscription_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if not course.course_file:
        messages.error(request, "This course does not have a file associated with it.")
        return redirect('home')
    # Convert markdown to HTML
    description_html = mark_safe(markdown.markdown(course.description))

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'description_html': description_html
    })

@login_required
def courses(request):
    courses = Course.objects.all()
    query = request.GET.get('q')
    
    context = {
        'courses': courses,
        'query': query or '',
    }
    if query:
        courses = courses.filter(title__icontains=query)
        context['courses'] = courses
    return render(request, 'courses/courses.html', context)


def navbar(request):
    # Get unique exam types that have exams
    exam_types = ExamType.objects.filter(exam__isnull=False, exam__for_scheduling=False).distinct().order_by('order')
    
    # Prefetch related exams for each type
    exam_types = exam_types.prefetch_related('exam_set')
    num = exam_types.count()
    
    context = {
        'exam_types': exam_types,
        'num':num
    }
    return render(request, 'default-navbar.html', context)

class SubscriptionRequiredView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_subscribed and not request.user.is_staff:
            messages.error(request, "Gura ifatabuguzi kugirango ubashe gukomeza!")
            return redirect('subscription')
        return super().dispatch(request, *args, **kwargs)

@login_required(login_url='login')
@subscription_required
def exam_detail(request, pk):
    exam_obj = get_object_or_404(Exam, pk=pk)
    if exam_obj.for_scheduling and hasattr(exam_obj, 'scheduledexam') and not exam_obj.scheduledexam.is_published:
        return render(request, '404.html', status=404)
    return render(request, 'exams/exam_detail.html', {'exam': exam_obj})

@staff_member_required
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
    return render(request, 'exams/exam_schedule.html', context)

def scheduled_hours(request):
    now = localtime(timezone.now())
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    exams_scheduled = ScheduledExam.objects.filter(
        scheduled_datetime__range=(start_of_day, end_of_day)
    )

    current_hour = now.hour
    pending = True
    
    if exams_scheduled.exists():
        for exam in exams_scheduled:
            if exam.scheduled_datetime.hour > current_hour:
                pending = True
                break

    completed_exam_ids = []
    if request.user.is_authenticated:
        completed_exam_ids = UserExam.objects.filter(
            user=request.user,
            completed_at__isnull=False
        ).values_list('exam_id', flat=True)

    context = {
        'exams_scheduled': exams_scheduled,
        'now': now,
        'current_hour': current_hour,
        'pending': pending,
        'completed_exam_ids': list(completed_exam_ids),
    }

    return render(request, 'scheduled_hours.html', context)

@require_GET
def check_exam_status(request, exam_id):
    try:
        exam = ScheduledExam.objects.get(id=exam_id)
        exam_time = timezone.localtime(exam.scheduled_datetime)
        return JsonResponse({
            "is_published": exam.is_published,
            "exam_url": reverse('exam_detail', kwargs={'pk': exam.exam.id}),  # Changed to kwargs
            "exam_time": exam_time.strftime("%H:00"),
            "remaining_time": exam.remaining_time

        })
    except ScheduledExam.DoesNotExist:  # Changed to match model name
        return JsonResponse({"error": "Exam not found"}, status=404)

def exam_timer(request, exam_id):
    try:
        scheduled_exam = ScheduledExam.objects.get(exam_id=exam_id)
        time_remaining = (scheduled_exam.scheduled_datetime - timezone.now()).total_seconds()
        return JsonResponse({'time_remaining': max(time_remaining, 0)})
    except ScheduledExam.DoesNotExist:
        return JsonResponse({'error': 'Exam not found'}, status=404)

@login_required(login_url='login')
def exams_by_type(request, exam_type):
    returned_exams = Exam.objects.filter(
        for_scheduling=False,
        exam_type__name=exam_type
    ).order_by('-updated_at')

    # Dictionary of completed exams: {exam_id: completed_at}
    completed_exams = UserExam.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).values('exam_id', 'completed_at')

    completed_exam_map = {
        item['exam_id']: item['completed_at'] for item in completed_exams
    }

    context = {
        'exam_type': exam_type,
        'returned_exams': returned_exams,
        'completed_exam_map': completed_exam_map,
        'counted_exams': returned_exams.count(),
    }    
    return render(request, "exams/same_exams.html", context)

@login_required(login_url='login')
@subscription_required
def ajax_question(request, exam_id, question_number):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = list(exam.questions.all())
    total_questions = len(questions)
    question = questions[question_number - 1]
    
    # Get choices
    choices = []
    for i in range(1, 5):
        choice_text = getattr(question, f'choice{i}_text', None)
        choice_sign = getattr(question, f'choice{i}_sign', None)
        if choice_text:
            choices.append({'type': 'text', 'content': choice_text, 'id': i})
        elif choice_sign:
            choices.append({'type': 'image', 'content': choice_sign.image_url, 'id': i})

    context = {
        'exam': exam,
        'question': question,
        'question_number': question_number,
        'total_questions': total_questions,
        'choices': choices,
        'questions': questions,
    }

    html = render_to_string('partials/question_block.html', context, request=request)
    return JsonResponse({'html': html})


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
    
    if exam.for_scheduling and hasattr(exam, 'scheduledexam') and not exam.scheduledexam.is_published:
        return render(request, '404.html', status=404)

    if user_exam.completed_at:
        return redirect('retake_exam', exam_id=exam_id)

    if question_number < 1 or question_number > total_questions:
        messages.error(request, "Invalid question number.")
        return redirect('exam', exam_id=exam_id, question_number=1)

    current_question = questions[question_number - 1]

    # Time left for countdown
    if not request.user.is_staff:
        exam_end_time = (user_exam.started_at + timedelta(minutes=exam.duration)).timestamp()

    # Initialize answer session if not present
    if 'answers' not in request.session:
        request.session['answers'] = {}

    # Handle answer submission and navigation
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        if user_answer:
            request.session['answers'][str(current_question.id)] = user_answer
            request.session.modified = True

        if 'next' in request.POST and question_number < total_questions:
            return redirect('exam', exam_id=exam_id, question_number=question_number + 1)
        elif 'previous' in request.POST and question_number > 1:
            return redirect('exam', exam_id=exam_id, question_number=question_number - 1)
        elif 'go_to' in request.POST:
            go_to_question = int(request.POST['go_to'])
            if 1 <= go_to_question <= total_questions:
                return redirect('exam', exam_id=exam_id, question_number=go_to_question)
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
            messages.success(request, f"Ikizamini cyarangiye! Ugize amanota: {score}/{total_questions}.")
            return redirect('exam_results', user_exam_id=user_exam.id)

    q_nums = range(1, total_questions + 1)

    # Prepare choices for current question
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
        'q_nums': q_nums,
        'total_questions': total_questions,
        'choices': choices,
        'exam_end_time': exam_end_time if not request.user.is_staff else None,
        'exam_duration': exam.duration * 60,
        'user_exam': user_exam,
        'questions': questions,
    }

    return render(request, 'exams/exam.html', context)

@login_required(login_url='login')
def exam_results(request, user_exam_id):
    user_exam = get_object_or_404(UserExam, id=user_exam_id, user=request.user)
    answers = UserExamAnswer.objects.filter(user_exam=user_exam).select_related('question')

    context = {
        'user_exam': user_exam,
        'answers': answers,
        'total_questions': user_exam.exam.questions.count(),
        'score': user_exam.score,
        'time_taken' : user_exam.time_taken,
        'percentage' : user_exam.percent_score,
        'decision' : user_exam.is_passed,
    }
    return render(request, 'exams/exam_results.html', context)

@login_required(login_url='login')
@subscription_required
def retake_exam(request, exam_id):
    if not request.user.is_subscribed and not request.user.is_staff: 
        messages.error(request, mark_safe(
            "<h2>Gura ifatabuguzi kugirango ubashe gukomeza!</h2>"
        ))
        return redirect('subscription')
    
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.for_scheduling and hasattr(exam, 'scheduledexam') and not exam.scheduledexam.is_published:
        return render(request, '404.html', status=404)
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

        messages.info(request, "Gusubirampo ikizamini byemeye. amahirwe masa!")
        return redirect('exam', exam_id=exam_id, question_number=1)

    context = {
        'exam': exam,
        'user_exam': user_exam,
    }
    return render(request, 'exams/confirm_retake_exam.html', context)

def get_weekly_scheduled_exams():
    now = timezone.now()
    start_of_week = now - timedelta(days=now.weekday() + 1)  # Monday
    end_of_week = start_of_week + timedelta(days=7)      # Sunday

    return ScheduledExam.objects.filter(
        scheduled_datetime__range=(start_of_week, end_of_week),
        scheduled_datetime__lte=now
    ).select_related('exam', 'exam__exam_type').order_by('-scheduled_datetime')

@login_required(login_url='login')
def weekly_exams(request):
    exams = get_weekly_scheduled_exams()

    # Get a list of tuples: (exam_id, completed_at)
    user_exam_data = UserExam.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).values_list('exam_id', 'completed_at')

    # Convert to a dictionary: {exam_id: completed_at}
    attempted_exams = {exam_id: completed_at for exam_id, completed_at in user_exam_data}

    # Attach status and time to each exam
    for exam in exams:
        exam_id = exam.exam.id
        exam.attempted = exam_id in attempted_exams
        exam.completed_at = attempted_exams.get(exam_id)

    context = {
        'exams': exams,
    }
    return render(request, 'exams/weekly_exams.html', context)


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_method = request.POST.get('contact_method')
        email = request.POST.get('email', '').strip()
        whatsapp = request.POST.get('whatsapp', '').strip()
        message_text = request.POST.get('message')

        if contact_method == 'email' and not email:
            messages.error(request, "Andika imeyili yawe nkuko wabihisempo.")
            return redirect('contact')
        elif contact_method == 'whatsapp' and not whatsapp:
            messages.error(request, "Andika nimero ya WhatsApp nkuko wabihisempo.")
            return redirect('contact')
        elif not contact_method:
            messages.error(request, "Hitamo uburyo bwo kugusubizaho.")
            return redirect('contact')

        ContactMessage.objects.create(
            name=name,
            email=email if contact_method == 'email' else None,
            whatsapp_number=whatsapp if contact_method == 'whatsapp' else None,
            message=message_text
        )
        messages.success(request, "Ubutumwa bwawe bwoherejwe neza! Tuzagusubiza vuba.")
        return redirect('contact')

    return render(request, 'contact.html')


def check_unique_field(request):
    field = request.GET.get("field")
    value = request.GET.get("value")
    response = {"exists": False}

    if field == "email" and value:
        response["exists"] = User.objects.filter(email__iexact=value).exists()
    elif field == "phone_number" and value:
        
        if len(value) >= 10:
            response["exists"] = User.objects.filter(phone_number__icontains=value).exists()
        # response["exists"] = User.objects.filter(phone_number__contains=value).exists()
    elif field == "name" and value:
        response["exists"] = User.objects.filter(name__iexact=value).exists()

    return JsonResponse(response)


@redirect_authenticated_users
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password1"])
            user.save()

            # Store user ID in session for WhatsApp consent step
            request.session['new_user_id'] = user.id
            
            if form.cleaned_data.get("phone_number"):
                user.otp_verified = True  
                user.save()
                messages.success(request, 'Kwiyandikisha muri Kigali Driving School byagenze neza')
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('whatsapp_consent')
                # return render(request, 'registration/register.html', {'registration_success': True})

            if form.cleaned_data.get("email"):
                try:
                    user.send_otp_email()
                    messages.success(request, 'Code isuzuma yoherejwe kuri email. Yandike hano.')
                    return redirect('verify_otp', user_id=user.id)
                except Exception as e:
                    form.add_error('email', "Imeri wanditse ntago ibasha koherezwaho code. Ongera usuzume neza.")
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})



def whatsapp_consent(request):
    #Redirect if the user has already given consent
    if request.user.whatsapp_consent:
        return redirect('home')

    # Get the newly registered user from the session
    user_id = request.session.get('new_user_id')
    if not user_id:
        return redirect('register')

    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User not found. Please register again.')
        return redirect('register')

    if request.method == 'POST':
        form = WhatsAppConsentForm(request.POST)

        if form.is_valid():
            
            if form.cleaned_data['consent'] == 'yes':
                user.whatsapp_consent = True
                user.whatsapp_notifications = True
                phone = form.cleaned_data.get('whatsapp_number')
                if phone:
                    valid_phone = validate_phone_number(phone)
                    
                    if not valid_phone:
                        messages.error(request, 'Niba uhitampo yego, Andika nimero ya whatsapp neza!')
                        return render(request, 'registration/whatsapp_consent.html', {'form': form, 'user': user})
                    
                    user.whatsapp_number = phone
                    user.save(update_fields=['whatsapp_number'])                                       
                    notify_admin(f"{user.name} consented to WhatsApp notifications with number: {phone}")
                    messages.success(request, "Wemeye kubona ubutumwa  bw'ikizamini gishya kuri WhatsApp. Urakoze!")
            else:
                user.whatsapp_consent = False
                user.whatsapp_notifications = False
                messages.info(request, "Urakoze kwiyandikisha, amahirwe masa mu masomo yawe!")

            user.save()
            return redirect('home')

    else:
        form = WhatsAppConsentForm()

    return render(request, 'registration/whatsapp_consent.html', {
        'form': form,
        'user': user
    })


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

            messages.success(request, 'Kwemeza email yawe byakunze. uhawe ikaze!')
            return redirect('home')
        else:
            messages.error(request, 'Code ntago ariyo, ongera ugerageze.')
    return render(request, 'registration/verify_otp.html', {'user': user_profile})


@redirect_authenticated_users
def login_view(request):
    page='login'
    
    # show_modal = request.GET.get('login') is not None
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
                    messages.success(request, "Kwinjira bikozwe neza cyane! Ikaze nanone.")
                    return redirect("home")
                else:
                    messages.error(request, "Ijambobanga ritariryo, ongera ugerageze.")
            else:
                messages.error(request, "Iyi konti ntago ibaho, Gusa wayihanga. <a href='/register/''>Hanga konti</a>")

        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = LoginForm()
        
    context = {
        "form": form,
        "page":page
    }
    return render(request, "base.html",context)


@require_POST
@login_required(login_url='login')
def user_logout(request):
    logout(request)
    messages.info(request, "Gusohoka byakunze.")
    return redirect('login')


# ---------------------
@login_required(login_url='login')
def payment(request):
    first_exam_id = Exam.objects.filter(exam_type__name__icontains='ibivanze').order_by('created_at').first().id
    plans = Plan.PLAN_CHOICES
    context = {
        'plans': plans,
        'range_10': range(10),
        'first_exam_id': first_exam_id,
    }
    return render(request, 'payment.html', context)
# ---------------------
# Subscription and Payment Views
# ---------------------

@login_required(login_url='/?login=true')
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


class PrivacyPolicyView(View):
    def get(self, request):
        return render(request, 'privacy_policy.html')


def base_view(request):
    
    context = {
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'base.html', context)

@staff_member_required
@require_POST
def undo_last_exam_action(request):
    exam_ids = request.session.get('undo_exam_ids', [])

    if exam_ids:
        Exam.objects.filter(id__in=exam_ids).delete()
        messages.success(request, "✅ Undo successful! Exams deleted.")
        request.session.pop('undo_exam_ids')
    else:
        messages.warning(request, "⚠️ No recent exams to undo.")

    return redirect('create_exam')


@login_required(login_url='login')
@staff_member_required
def create_exam_page(request):
    if request.method == 'POST':
        try:
            number = int(request.POST.get("number", 0))
            if number <= 0:
                raise ValueError("Number must be greater than 0")
            
            exams_created, created_exam_ids = auto_create_exams(number)
            request.session['undo_exam_ids'] = created_exam_ids
            request.session['show_undo'] = True  # Add flag

            messages.success(request, f"{exams_created} exam(s) created successfully!")
            return redirect('create_exam')
        except (ValueError, TypeError):
            messages.error(request, "Invalid number of exams.")

    # Show last 10 Ibivanze exams
    ibivanze_type = ExamType.objects.filter(name='Ibivanze').first()
    recent_exams = Exam.objects.filter(exam_type=ibivanze_type).order_by('-created_at')[:10]
    
    context = {
        'recent_exams': recent_exams,
        'show_undo': request.session.pop('show_undo', False),
        'has_undo_ids': bool(request.session.get('undo_exam_ids')),
    }
    return render(request, 'exams/create_exam.html', context)


@staff_member_required
def schedule_recent_exams(request):
    
    if request.method == 'POST':
        
        _ , message =  auto_schedule_recent_exams()

        messages.success(request, message)
        return redirect('auto_schedule_exams')  # Or redirect to a success page

    return render(request, 'exams/schedule_recent_exams.html')

# ---------------------
#404 Error Page
def custom_page_not_found(request, exception):
    
    context = {}
    return render(request, '404.html', context, status=404)


@csrf_exempt  # We exempt this view from CSRF since it handles CSRF failures
def csrf_failure(request, reason=""):
    ctx = {
        'reason': reason,
        'csrf_token': get_token(request),  # Generate new token
    }
    return render(request, '403.html', ctx, status=403)



@csrf_exempt
@login_required
def resend_otp(request, user_id):
    if request.method == "POST":
        user_profile = get_object_or_404(UserProfile, id=user_id)
        # Logic to resend OTP (e.g., send email or SMS)
        user_profile.send_otp_email()  # Assuming you have a method to send OTP
        return JsonResponse({"message": "OTP resent successfully."}, status=200)
    return JsonResponse({"error": "Invalid request."}, status=400)
