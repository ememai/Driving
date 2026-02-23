from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
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
from django.db import transaction
from .authentication import EmailOrPhoneBackend  # Import the custom backend
from django.utils.timezone import now, localtime, make_aware
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from django.views import View
from django.views.decorators.http import require_POST, require_GET
from datetime import datetime, timedelta, time, date
import random
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.http import JsonResponse,FileResponse,Http404
from .utils import *
import mimetypes
import markdown
from wsgiref.util import FileWrapper
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
# from django.contrib.auth.forms import CustomSetPasswordForm
from django.views.decorators.csrf import csrf_exempt



User = get_user_model()

# avoid querying at import time without guarding for empty queryset
# during tests there may be no exams yet, so ensure we don't crash

def _get_first_exam_id():
    exam = Exam.objects.filter(
        exam_type__name__icontains='ibivanze',
        for_scheduling=False,
    ).order_by('created_at').first()
    return exam.id if exam else None

first_exam_id = _get_first_exam_id()


def home(request):
    exam_types = ExamType.objects.filter(
        exam__isnull=False, 
    ).distinct().order_by('order')

    # Annotate each exam type with the count of non-scheduled exams
    exam_types = exam_types.annotate(
        actual_exam_count=Count('exam',)
    )
    
    unpublished_count = ScheduledExam.objects.filter(
        scheduled_datetime__gt=timezone.now(), exam__for_scheduling=True
    ).count()
    
    
    for exam_type in exam_types:
        exam_type.actual_exam_count -= unpublished_count if exam_type.name.lower() == 'ibivanze' else 0
        if exam_type.actual_exam_count > 1000:
            exam_type.actual_exam_count = "1000+"
    

     # Prefetch related exams for each type
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

@redirect_authenticated_users
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # user.set_password(form.cleaned_data["password1"])
            user.save()

            # Store user ID in session for WhatsApp consent step
            request.session['new_user_id'] = user.id
            
            if form.cleaned_data.get("phone_number"):
                user.otp_verified = True  
                user.save()
                messages.success(request, 'Kwiyandikisha ku igazeti.rw byagenze neza')
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
    # elif field == "name" and value:
    #     response["exists"] = User.objects.filter(name__iexact=value).exists()

    return JsonResponse(response)


def whatsapp_consent(request):
    #Redirect if the user has already given consent
    if request.user.whatsapp_consent:
        return redirect('home')

    # Get the newly registered user from the session
    user_id = request.session.get('new_user_id')
    if not user_id:
        return redirect('register')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
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
            # Clear the session variable
            del request.session['new_user_id']
            if request.GET.get('next'):
                return redirect(request.GET.get('next'))
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
    page = 'login'
    
    if request.method == "POST":
        form = LoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data.get("password", "")  # Password is optional
            
            # Normalize phone number if needed
            if "@" not in username:  
                username = EmailOrPhoneBackend().normalize_phone_number(username)

            # Fetch user by email or phone number
            user = User.objects.filter(
                Q(phone_number=username) | Q(email=username)
            ).first()
            
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

                    if request.GET.get('next'):
                        return redirect(request.GET.get('next'))
                    return redirect('home')

                elif user.requires_password:
                    messages.error(request, "Permission required")
            else:
                register_link = mark_safe('<a href="/register" class="alert-link">Hanga konti</a>')
                messages.error(request, f"Iyi konti ntago ibaho, Gusa wayihanga. {register_link}")

        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = LoginForm()
        
    context = {
        "form": form,
        "page": page
    }
    return render(request, "base.html", context)

@require_POST
@login_required(login_url='register')
def user_logout(request):
    logout(request)
    messages.info(request, "Gusohoka byakunze.")
    return redirect('login')


@csrf_exempt
def password_reset(request):
    
    if request.method == "POST":
        phone_number = clean_phone_number(request.POST.get("phone_number"))

        if not phone_number:
            messages.error(request, "Andika numero ya telefone.")
            return redirect("password_reset")

        try:
            # Find user by phone
            user = UserProfile.objects.get(phone_number=phone_number)
        except UserProfile.DoesNotExist:
            messages.error(request, "Nta konti ifunguye kuri iyi nimero ya telefone. Ongera usuzume neza!")
            return redirect("password_reset")

        # Generate token and reset link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = request.build_absolute_uri(
            reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        )

        # Send the link to admin (not to user)
        notify_admin(f"🔐 Password reset request for {user.name} ({user.phone_number})\nLink: {reset_url}")

        messages.success(
            request,
            "Link yo guhindura ijambobanga yoherejwe, reba kuri WhatsApp cyangwa sms yawe. Niba utabona link, saba ubufasha 0785287885.",
        )
        return redirect("login")

    return render(request, "registration/password_reset.html")

def password_reset_confirm(request, uidb64, token):
    """
    Step 2: User (or admin) opens the reset link and sets a new password.
    """
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserProfile.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserProfile.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Ijambo ry'ibanga ryahinduwe neza. rikoreshe winjira.")
                return redirect("login")
        else:
            form = CustomSetPasswordForm(user)
        return render(request, "registration/password_reset_confirm.html", {"form": form})
    else:
        messages.error(request, "Link ntabwo ikiri valid cyangwa yararenze igihe.")
        return redirect("login")


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


# @login_required(login_url='register')
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
@subscription_required
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

# @login_required(login_url='register')
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
        scheduled_datetime__range=(start_of_day, end_of_day),        
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

@login_required(login_url='register')
def exams_by_type(request, exam_type):
    returned_exams = Exam.objects.filter(
        exam_type__name=exam_type
    ).exclude(
        Q(for_scheduling=True) & Q(scheduledexam__scheduled_datetime__gt=timezone.now())
    ).order_by('-updated_at')

    # Dictionary of completed exams: {exam_id: completed_at}
    completed_exams = UserExam.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).values('exam_id', 'completed_at')

    completed_exam_map = {
        item['exam_id']: item['completed_at'] for item in completed_exams
    }
    
    mixed_exam_types = 'ibivanze'
    context = {
        'exam_type': exam_type,
        'returned_exams': returned_exams,
        'completed_exam_map': completed_exam_map,
        'counted_exams': returned_exams.count(),
        'mixed_exam_types': mixed_exam_types,
    }    
    return render(request, "exams/same_exams.html", context)


@login_required(login_url='register')
@subscription_required
def ajax_question(request, exam_id, question_number):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = list(exam.questions.all())
    total_questions = len(questions)
    
    if question_number < 1 or question_number > total_questions:
        return JsonResponse({'error': 'Invalid question number'}, status=400)
    
    question = questions[question_number - 1]
    
    if not request.user.is_subscribed and not request.user.is_staff: 
        if question_number >= 2 or request.session.get('answers') and len(request.session['answers']) >= 1:
            UserExam.objects.filter(user=request.user, exam=exam).delete()
            request.session.pop('answers', None)     
            messages.error(request, mark_safe(
               "<h5>Gura ifatabuguzi kugirango ukomeze ikizamini!</h5>"
            ))       
            return JsonResponse({'redirect': reverse('subscription')})
    
    
    # Handle answer saving if POST request
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        question_id = request.POST.get('question_id')
        if 'answers' not in request.session:
            request.session['answers'] = {}
        if user_answer and question_id:
            request.session['answers'][question_id] = user_answer
            request.session.modified = True
    
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


@login_required(login_url='register')
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
        
    if question_number >= 2 and not request.user.is_subscribed or request.session['answers'].__len__() >= 1 and not request.user.is_subscribed and not request.user.is_staff:
                UserExam.objects.filter(id=user_exam.id).delete()
                request.session.pop('answers', None)            
                messages.error(request, mark_safe(
                   "<h5>Gura ifatabuguzi kugirango ukomeze ikizamini!</h5>"
                ))
                return redirect('subscription')

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
        
        elif 'submit' in request.POST:
            score = 0
            if not request.user.is_subscribed and not request.user.is_staff:
                UserExam.objects.filter(id=user_exam.id).delete()
                request.session.pop('answers', None)            
                # messages.error(request, mark_safe(
                #    "<h5>Ntago wemerewe!</h5>"
                # ))
                return redirect('subscription')
            
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

        elif 'go_to' in request.POST:
            go_to_question = int(request.POST['go_to'])
            if 1 <= go_to_question <= total_questions:
                return redirect('exam', exam_id=exam_id, question_number=go_to_question)
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

@login_required(login_url='register')
@subscription_required
def exam_results(request, user_exam_id):
    
    user_exam = get_object_or_404(UserExam, id=user_exam_id, user=request.user)
    
    if not request.user.is_subscribed and not user_exam.exam.id == first_exam_id:
        messages.error(request, mark_safe(
            f"<span>Iki kizamini ufite amanota</span> {user_exam.score}<br><h5>Gura ifatabuguzi kugirango ubashe kureba byose!</h5>"
        ))
        return redirect('subscription')
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

@login_required(login_url='register')
@subscription_required
def retake_exam(request, exam_id):
    if not request.user.is_subscribed and not request.user.is_staff: 
        messages.error(request, mark_safe(
            "<h5>Gura ifatabuguzi kugirango ubashe gusubirampo ikizamini!</h5>"
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

@login_required(login_url='register')
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
        
        validated_number = validate_phone_number(whatsapp) if whatsapp else None
        
        if whatsapp and not validated_number:
            messages.error(request, "Andika nimero ya WhatsApp neza.")
            return redirect('contact')

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
            whatsapp_number=validated_number if contact_method == 'whatsapp' else None,
            message=message_text
        )
        messages.success(request, "Ubutumwa bwawe bwoherejwe neza! Turagusubiza vuba.")
        notify_admin(f"New contact message from {name} via {contact_method}\n\n msg: *{message_text}* \n\ncontact: {email or whatsapp}")
        return redirect('contact')

    return render(request, 'contact.html')

def get_unverified_subscription(user):
    subscription = Subscription.objects.filter(
        user=user, 
        otp_code__isnull=False,
        otp_verified=False).first()
    return subscription

# ---------------------
@login_required(login_url='register')
def payment(request):
    page = 'payment'
    all_plans=Plan.objects.all().order_by('price')
    context = {
        'all_plans': all_plans,
        'range_10': range(10),
        'first_exam_id': first_exam_id,
        'page': page,
    }
    return render(request, 'payment.html', context)


@login_required(login_url='register')
def recreate_otp(request):
    unverified_subscription = get_unverified_subscription(request.user)
    if unverified_subscription:
        unverified_subscription.generate_otp()
        messages.success(request, "Code nshya yoherejwe neza!.")
        return redirect('activate_subscription')
    else:
        messages.error(request, "Nta ifatabuguzi ritaremezwa ribonetse.")
        return redirect('subscription')

@login_required(login_url='register')
def subscription_status(request): 
    show_modal = request.GET.get('confirm') == '1'
    page = 'subscription_status'
    plans = Plan.PLAN_CHOICES
    unverified_subscription = get_unverified_subscription(request.user)
    context = {'page': page,
        'plans': plans,
        'range_10': range(10),
        'first_exam_id': first_exam_id,
        'unverified_subscription' : unverified_subscription,
        'show_modal':show_modal
        }    
    return render(request, 'payment.html', context)
# ---------------------
# Subscription and Payment Views
# ---------------------


@login_required(login_url='register')
@transaction.atomic
def payment_confirm(request):
    
    if request.method == 'POST':
        try:
            payeer_name = request.POST.get('payeer_name', '').strip()
            payeer_phone = request.POST.get('payeer_phone', '').strip()
            plan_choice = request.POST.get('plan', '').strip()
            whatsapp_number = request.POST.get('whatsapp_number', '').strip()
            
            
            # Validate phone numbers
            try:
                validate_phone_number(payeer_phone)
                validate_phone_number(whatsapp_number)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'payment.html', {'first_exam_id': first_exam_id})
            
            # Get plan
            try:
                plan = Plan.objects.get(price=plan_choice)
            except Plan.DoesNotExist:
                messages.error(request, "Server error")
                return render(request, 'payment.html', {'first_exam_id': first_exam_id})
            
            # Create/update payment confirmation
            PaymentConfirm.objects.update_or_create(
                user=request.user,
                defaults={
                    'payeer_name': payeer_name,
                    'phone_number': payeer_phone,
                    'plan': plan,
                    'whatsapp_number': whatsapp_number,
                    'time': timezone.now()
                }            
            )            
            if hasattr(request.user, 'subscription'):
                
                if request.user.subscription.otp_verified == False and request.user.subscription.otp_code:
                    messages.info(request, f"Ubwishyu bwawe bwemejwe.")
                    return redirect('activate_subscription')
                
                msg = "Renewal"
                
                if request.user.subscription.plan.plan == plan.plan:
                    link = request.build_absolute_uri(reverse('dashboard_renew_subscription', args=[request.user.subscription.id]))
                else:
                    # link = request.build_absolute_uri(reverse('admin:app_subscription_change', args=[request.user.subscription.id]))
                    link = request.build_absolute_uri(reverse('subscription_update', args=[request.user.subscription.id]))

            else:
                msg = "New"
                link = request.build_absolute_uri(reverse('approve_payment', args=[request.user.id, plan.id]))
            
            notify_admin(f'''{msg} payment confirmation from {request.user.name},\n\n -Payeer name: {payeer_name}\n -Payed 4ne: {payeer_phone}, \nplan: {plan},\n\nApprove at: {link}\n\nWhatsapp: {whatsapp_number}''')
            
            messages.success(request, f"Kwemeza ubwishyu byoherejwe neza! Urakira igisubizo mu munota umwe.")
            return redirect('home')
            
        except Exception as e:
            messages.error(request, "Server error, kindly contact us on 0785287885 for support.")
    
    return redirect(f"{reverse('subscription')}?confirm=1")


#approve payment and create subscription
@transaction.atomic
@staff_member_required
@csrf_exempt
def approve_payment(request, user_id, plan_id):
    """Approve payment and create/update subscription with OTP verification."""
    try:
        user = User.objects.get(id=user_id)
        requested_plan = Plan.objects.get(id=plan_id)
        all_plans = Plan.objects.all().order_by('price')
    except (User.DoesNotExist, Plan.DoesNotExist):
        messages.error(request, "User or Plan does not exist.")
        return redirect('admin:app_paymentconfirm_changelist')

    if request.method == 'POST':
        return _handle_payment_approval(request, user, requested_plan)

    return render(request, 'admin/approve_payment.html', {
        'user': user,
        'plan': requested_plan,
        'plans': all_plans
    })


def _handle_payment_approval(request, user, requested_plan):
    """Handle POST request for payment approval."""
    subscription, _ = Subscription.objects.get_or_create(user=user)
    
    # Get plan from POST data or use requested plan
    plan_id = request.POST.get('plan_instance')
    if plan_id:
        try:
            subscription.plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            messages.error(request, "Selected plan does not exist.")
            return redirect('subscription')
    else:
        subscription.plan = requested_plan
    
    subscription.generate_otp()
    subscription.save()
    
    
    messages.success(request, f"Payment approved and subscription created for {user.name}.")
    return redirect('admin:app_subscription_changelist')

# @login_required(login_url='/?login=true')
# def subscription_view(request):
#     # sub = request.user.subscription and request.user.subscription.expires_at > timezone.now().date()

#     subscription, created = Subscription.objects.get_or_create(user=request.user)
#     if request.method == 'POST':
#         plan_choice = request.POST.get('plan')
#         phone_number = request.POST.get('phone_number')

#         if plan_choice not in dict(plans):
#             messages.error(request, "Ikiciro kitaricyo.")
#             return redirect('subscription')

#         try:
#             selected_plan = Plan.objects.get(plan=plan_choice)
#         except Plan.DoesNotExist:
#             messages.error(request, "Ikiciro wahisempo ntikibaho.")
#             return redirect('subscription')

#         # This function should return (price, duration_days) for the selected plan.
#         price, duration_days = set_price_and_duration(plan_choice)  # Ensure this helper exists.

#         payment_response, transaction_id = request_momo_payment(phone_number, price)
#         if "error" in payment_response:
#             messages.error(request, payment_response["error"])
#             return redirect('subscription')

#         # Save transaction details
#         subscription.plan = selected_plan  # ✅ Assign the Plan instance
#         subscription.price = price
#         subscription.duration_days = duration_days
#         subscription.phone_number = phone_number
#         subscription.transaction_id = transaction_id
#         subscription.save()


#         messages.info(request, "Kwemeza ubwishyu byoherejwe. reba kuri telefone wemeze.")
#         return redirect('momo_payment_status', transaction_id=transaction_id)

#     context = {
#         'subscription': subscription,
#         'plans': plans,
#         # 'sub': sub
#     }
#     return render(request, 'subscription.html', context)

@login_required
def activate_subscription_view(request):
    context = {}
    unverified_subscription = get_unverified_subscription(request.user)
    if unverified_subscription:
        user_otp = unverified_subscription.otp_code
        context['user_otp'] = user_otp
    else:
        return redirect('subscription')

    if request.method == "POST":
        otp = request.POST.get("otp")
        try:
            subscription = Subscription.objects.get(user=request.user, otp_verified=False)
        except Subscription.DoesNotExist:
            otp_used = Subscription.objects.filter(user=request.user, otp_verified=True, otp_code=otp).exists()
            subscription = Subscription.objects.filter(user=request.user, otp_verified=True).first()
            otp_used_at = localtime(subscription.started_at).strftime("%d-%m-%Y Saa %H:%M") if otp_used else None
            
            expires_at = localtime(subscription.expires_at).strftime("%d-%m-%Y Saa %H:%M") if subscription else "N/A"
            contact = ""
            
            Error_type = f"Code wamaze kuyikoresha!!!" if otp_used else "Code ntago ariyo!!!"
            context.update({
                "show_modal": True,
                "Error_type": Error_type,
                "modal_title": f"Error: {Error_type}",                
                "modal_message": f'''                
                 <br> ifatabuguzi ryafunguwe Taliki:
                <strong>{otp_used_at}</strong> <br>
                kugeza Taliki: <strong>{expires_at}</strong>'''
                if otp_used else f"Ongera ugerageze!",
                "redirect_url": reverse("activate_subscription"),
            })
            return render(request, "activate_subscription.html", context)

        success, message, expires_at = subscription.verify_and_start(otp)
        if success:
            # Get human-readable plan name
            plan_display = dict(Plan.PLAN_CHOICES).get(subscription.plan.plan, subscription.plan.plan)
            today = timezone.now().date()
            expires_date = "Taliki " + localtime(expires_at).strftime('%d-%m-%Y') if expires_at.date() != today else ''
            expires_hour = localtime(expires_at).strftime('%H:%M')
            
                
            context.update({
                "show_modal": True,
                "modal_title": f"Ifatabuguzi <strong>'{plan_display}'</strong> riratangiye🎉",
                "modal_message": f'''{message} Ubu wemerewe kwiga no gukosora ibizamini ushaka kugeza <br> 
                <strong>{expires_date} Saa {expires_hour} </strong>''',
                "redirect_url": reverse("home"),
            })
        else:
            context.update({
                "show_modal": True,
                "modal_title": "Error",
                "modal_message": message,
                "redirect_url": reverse("subscription"),
            })

    return render(request, "activate_subscription.html", context)


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


@login_required(login_url='register')
@staff_member_required
def create_exam_page(request, exam_id=None):
    exam = None
    if exam_id:
        exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        try:
            schedule_hour = request.POST.get('schedule_hour')
            duration = int(request.POST.get('duration', 20))
            for_scheduling = 'for_scheduling' in request.POST
            
            if exam:
                # Update existing exam
                exam.schedule_hour = schedule_hour
                exam.duration = duration
                exam.for_scheduling = for_scheduling
                exam.save()
                messages.success(request, "Exam updated successfully!")
            else:
                # Create new exam
                exam_type = ExamType.objects.get_or_create(name='Ibivanze')[0]
                questions = Question.objects.order_by('?')[:20]
                if questions.count() < 20:
                    messages.error(request, "Not enough questions available.")
                    return redirect('create_exam')
                
                exam = Exam.objects.create(
                    exam_type=exam_type,
                    schedule_hour=schedule_hour,
                    duration=duration,
                    for_scheduling=for_scheduling,
                )
                exam.questions.set(questions)
                messages.success(request, "Exam created successfully!")
            
            return redirect('create_exam')
        except (ValueError, TypeError) as e:
            messages.error(request, f"Invalid input: {e}")

    # Show last 10 Ibivanze exams
    ibivanze_type = ExamType.objects.filter(name='Ibivanze').first()
    recent_exams = Exam.objects.filter(exam_type=ibivanze_type).order_by('-created_at')[:10]
    
    context = {
        'recent_exams': recent_exams,
        'exam': exam,
    }
    return render(request, 'exams/create_exam.html', context)

# --- Exam Edit and Delete Views ---

@login_required(login_url='register')
@staff_member_required
@require_POST
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam.delete()
    messages.success(request, "Exam deleted successfully.")
    return redirect('create_exam')

@staff_member_required
def schedule_recent_exams(request):
    
    if request.method == 'POST':
        
        _ , message =  auto_schedule_recent_exams()
    
        messages.success(request, message)
        return redirect('auto_schedule_exams')  # Or redirect to a success page

    return render(request, 'exams/schedule_recent_exams.html')

@login_required(login_url='register')
@staff_member_required
def manage_scheduled_exams(request, scheduled_exam_id=None):
    scheduled_exam = None
    if scheduled_exam_id:
        scheduled_exam = get_object_or_404(ScheduledExam, id=scheduled_exam_id)
    
    if request.method == 'POST':
        try:
            exam_id = request.POST.get('exam')
            scheduled_datetime_str = request.POST.get('scheduled_datetime')
            
            exam = get_object_or_404(Exam, id=exam_id)
            scheduled_datetime = parse_datetime(scheduled_datetime_str)
            
            if scheduled_datetime is None:
                raise ValueError("Invalid date/time format")
            
            # Make the datetime timezone-aware if it's naive
            if timezone.is_naive(scheduled_datetime):
                scheduled_datetime = make_aware(scheduled_datetime)
            
            if scheduled_exam:
                # Update existing scheduled exam
                scheduled_exam.exam = exam
                scheduled_exam.scheduled_datetime = scheduled_datetime
                scheduled_exam.save()
                messages.success(request, "Scheduled exam updated successfully!")
            else:
                # Create new scheduled exam
                ScheduledExam.objects.create(
                    exam=exam,
                    scheduled_datetime=scheduled_datetime,
                )
                messages.success(request, "Exam scheduled successfully!")
            
            return redirect('manage_scheduled_exams')
        except (ValueError, TypeError) as e:
            messages.error(request, f"Invalid input: {e}")

    # Get all scheduled exams
    scheduled_exams = ScheduledExam.objects.select_related('exam').order_by('-scheduled_datetime')
    
    # Get available exams that can be scheduled (for_scheduling=True and not already scheduled)
    available_exams = Exam.objects.filter(
        for_scheduling=True
    ).exclude(
        id__in=ScheduledExam.objects.values_list('exam_id', flat=True)
    )
    
    context = {
        'scheduled_exams': scheduled_exams,
        'available_exams': available_exams,
        'scheduled_exam': scheduled_exam,
    }
    return render(request, 'exams/manage_scheduled_exams.html', context)

@login_required(login_url='register')
@staff_member_required
@require_POST
def delete_scheduled_exam(request, scheduled_exam_id):
    scheduled_exam = get_object_or_404(ScheduledExam, id=scheduled_exam_id)
    scheduled_exam.delete()
    messages.success(request, "Scheduled exam deleted successfully.")
    return redirect('manage_scheduled_exams')

@login_required(login_url='register')
@staff_member_required
@require_POST
def bulk_delete_scheduled_exams(request):
    selected_exams = request.POST.getlist('selected_exams')
    
    if not selected_exams:
        messages.error(request, "No exams selected for deletion.")
        return redirect('manage_scheduled_exams')
    
    try:
        # Convert to integers and validate
        exam_ids = [int(exam_id) for exam_id in selected_exams]
        
        # Get the scheduled exams
        scheduled_exams = ScheduledExam.objects.filter(id__in=exam_ids)
        deleted_count = scheduled_exams.count()
        
        # Delete them
        scheduled_exams.delete()
        
        messages.success(request, f"Successfully deleted {deleted_count} scheduled exam{'s' if deleted_count != 1 else ''}.")
    except (ValueError, TypeError):
        messages.error(request, "Invalid exam selection.")
    
    return redirect('manage_scheduled_exams')

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

@login_required
def check_unverified_subscription(request):
    has_unverified = None
    if not request.user.is_authenticated:
        return JsonResponse({'unverified': False, 'error': 'unauthenticated'}, status=401)
    
    unverified_sub = get_unverified_subscription(request.user)
    if unverified_sub:
        has_unverified = True
    print(has_unverified)
    return JsonResponse({'unverified': has_unverified})