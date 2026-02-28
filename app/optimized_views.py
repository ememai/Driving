"""
OPTIMIZED VIEWS - Performance Enhanced Views
Replace corresponding functions in app/views.py with these optimized versions
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.db.models import Prefetch, Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import (
    Exam, ExamType, Course, UserExam, UserExamAnswer, 
    ScheduledExam, Question, RoadSign
)
from .performance import paginate_results, cache_query


# ============================================================================
# OPTIMIZED HOME VIEW
# ============================================================================

def home_optimized(request):
    """Optimized home view with cached exam types"""
    
    # Try to get from cache first
    cache_key = 'home_page_data'
    context = cache.get(cache_key)
    
    if context is None:
        # Get exam types with proper joins
        exam_types = ExamType.objects.filter(
            exam__isnull=False,
        ).distinct().order_by('order').annotate(
            actual_exam_count=Count('exam')
        )
        
        # Get courses
        courses = Course.objects.all()
        query = request.GET.get('q')
        category = request.GET.get('category')

        if query:
            courses = courses.filter(title__icontains=query)

        if category:
            courses = courses.filter(category=category)

        # Cache the expensive part
        unpublished_count = ScheduledExam.objects.filter(
            scheduled_datetime__gt=timezone.now(), 
            exam__for_scheduling=True
        ).count()
        
        context = {
            'exam_types': list(exam_types),
            'num': exam_types.count(),
            'courses': list(courses),
            'query': query or '',
            'selected_category': category or '',
            'categories': Course._meta.get_field('category').choices,
            'unpublished_count': unpublished_count,
        }
        
        # Cache for 30 minutes if no query params
        if not query and not category:
            cache.set(cache_key, context, 1800)
    
    return render(request, 'home.html', context)


# ============================================================================
# OPTIMIZED EXAMS BY TYPE VIEW
# ============================================================================

@login_required(login_url='register')
def exams_by_type_optimized(request, exam_type):
    """
    Optimized view to get exams by type with pagination
    """
    # Use select_related and prefetch_related to optimize queries
    returned_exams = Exam.objects.filter(
        exam_type__name=exam_type
    ).exclude(
        Q(for_scheduling=True) & Q(scheduledexam__scheduled_datetime__gt=timezone.now())
    ).select_related('exam_type').prefetch_related(
        'questions__question_type'
    ).order_by('-updated_at')
    
    # Paginate results
    paginator, page_obj, is_paginated = paginate_results(returned_exams, request, per_page=15)
    
    # Get completed exams for the user (once instead of repeatedly)
    completed_exams = UserExam.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).values_list('exam_id', 'completed_at')
    
    completed_exam_map = {exam_id: completed_at for exam_id, completed_at in completed_exams}
    
    context = {
        'exam_type': exam_type,
        'returned_exams': page_obj.object_list,
        'completed_exam_map': completed_exam_map,
        'counted_exams': paginator.count,
        'mixed_exam_types': 'ibivanze',
        'page_obj': page_obj,
        'is_paginated': is_paginated,
    }
    
    return render(request, "exams/same_exams.html", context)


# ============================================================================
# OPTIMIZED AJAX QUESTION VIEW
# ============================================================================

@login_required(login_url='register')
@require_GET
def ajax_question_optimized(request, exam_id, question_number):
    """
    Optimized view to serve exam questions via AJAX
    """
    try:
        # Cache key for questions
        cache_key = f'exam_questions:{exam_id}'
        questions = cache.get(cache_key)
        
        if questions is None:
            exam = get_object_or_404(
                Exam.objects.select_related('exam_type').prefetch_related(
                    Prefetch(
                        'questions',
                        Question.objects.select_related(
                            'question_sign',
                            'choice1_sign',
                            'choice2_sign',
                            'choice3_sign',
                            'choice4_sign'
                        ).order_by('order')
                    )
                ),
                id=exam_id
            )
            questions = list(exam.questions.all())
            cache.set(cache_key, questions, 3600)  # Cache for 1 hour
        else:
            exam = get_object_or_404(Exam, id=exam_id)
        
        total_questions = len(questions)
        
        if question_number < 1 or question_number > total_questions:
            return JsonResponse({'error': 'Invalid question number'}, status=400)
        
        question = questions[question_number - 1]
        
        # Build choices
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
        }
        
        from django.template.loader import render_to_string
        html = render_to_string('partials/question_block.html', context, request=request)
        
        return JsonResponse({'html': html})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# OPTIMIZED EXAM RESULTS VIEW
# ============================================================================

@login_required(login_url='register')
def exam_results_optimized(request, user_exam_id):
    """
    Optimized view for displaying exam results with cached data
    """
    # Get user exam with related data in one query
    user_exam = get_object_or_404(
        UserExam.objects.select_related(
            'user',
            'exam__exam_type'
        ).prefetch_related(
            Prefetch(
                'userexamanswer_set',
                UserExamAnswer.objects.select_related('question')
            )
        ),
        id=user_exam_id,
        user=request.user
    )
    
    # Get answers from prefetched data
    answers = user_exam.userexamanswer_set.all()
    
    context = {
        'user_exam': user_exam,
        'answers': answers,
        'total_questions': user_exam.exam.questions.count(),
        'score': user_exam.score,
        'time_taken': user_exam.time_taken,
        'percentage': user_exam.percent_score,
        'decision': user_exam.is_passed,
    }
    
    return render(request, 'exams/exam_results.html', context)


# ============================================================================
# OPTIMIZED NAVBAR VIEW
# ============================================================================

def navbar_optimized(request):
    """
    Optimized navbar with cached exam types
    """
    cache_key = 'navbar_exam_types'
    exam_types = cache.get(cache_key)
    
    if exam_types is None:
        exam_types = ExamType.objects.filter(
            exam__isnull=False,
            exam__for_scheduling=False
        ).distinct().order_by('order').prefetch_related(
            Prefetch('exam_set', Exam.objects.filter(for_scheduling=False))
        )
        cache.set(cache_key, exam_types, 3600)  # Cache for 1 hour
    
    context = {
        'exam_types': exam_types,
        'num': len(exam_types),
    }
    
    return render(request, 'default-navbar.html', context)


# ============================================================================
# OPTIMIZED COURSES VIEW
# ============================================================================

@login_required(login_url='register')
def courses_optimized(request):
    """
    Optimized courses view with pagination
    """
    courses = Course.objects.all()
    query = request.GET.get('q')
    
    if query:
        courses = courses.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    
    # Paginate
    paginator, page_obj, is_paginated = paginate_results(courses, request, per_page=20)
    
    context = {
        'courses': page_obj.object_list,
        'query': query or '',
        'page_obj': page_obj,
        'is_paginated': is_paginated,
    }
    
    return render(request, 'courses/courses.html', context)


# ============================================================================
# OPTIMIZED COURSE DETAIL VIEW
# ============================================================================

def course_detail_optimized(request, slug):
    """
    Optimized course detail view with caching
    """
    cache_key = f'course_detail:{slug}'
    context = cache.get(cache_key)
    
    if context is None:
        course = get_object_or_404(Course, slug=slug)
        
        if not course.course_file:
            messages.error(request, "This course does not have a file associated with it.")
            return redirect('home')
        
        import markdown
        from django.utils.safestring import mark_safe
        
        description_html = mark_safe(markdown.markdown(course.description))
        
        context = {
            'course': course,
            'description_html': description_html
        }
        
        cache.set(cache_key, context, 3600)  # Cache for 1 hour
    
    return render(request, 'courses/course_detail.html', context)


# ============================================================================
# OPTIMIZED SCHEDULED HOURS VIEW
# ============================================================================

def scheduled_hours_optimized(request):
    """
    Optimized view for scheduled exam hours
    """
    now = timezone.localtime(timezone.now())
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Single optimized query
    exams_scheduled = ScheduledExam.objects.filter(
        scheduled_datetime__range=(start_of_day, end_of_day),
    ).select_related('exam__exam_type')
    
    current_hour = now.hour
    pending = True
    
    if exams_scheduled.exists():
        for exam in exams_scheduled:
            if exam.scheduled_datetime.hour > current_hour:
                pending = True
                break
    
    # Get completed exam IDs once
    completed_exam_ids = []
    if request.user.is_authenticated:
        completed_exam_ids = list(
            UserExam.objects.filter(
                user=request.user,
                completed_at__isnull=False
            ).values_list('exam_id', flat=True)
        )
    
    context = {
        'exams_scheduled': exams_scheduled,
        'now': now,
        'current_hour': current_hour,
        'pending': pending,
        'completed_exam_ids': completed_exam_ids,
    }
    
    return render(request, 'scheduled_hours.html', context)
