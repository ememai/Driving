# your_app/api.py
from django.http import JsonResponse
from .models import Question

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def get_questions_for_exam_type(request):
    exam_type_id = request.GET.get('exam_type_id')
    if not exam_type_id:
        return JsonResponse({'error': 'exam_type_id parameter required'}, status=400)
    
    questions = Question.objects.filter(
        question_type_id=exam_type_id
    ).order_by('order')
    
    data = {
        'questions': [
            {
                'id': q.id,
                'text': str(q),  # Uses your Question model's __str__ method
                'type': q.question_type.name if q.question_type else None
            }
            for q in questions
        ]
    }
    return JsonResponse(data)