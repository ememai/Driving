# dashboard/forms.py
from django import forms
from django.utils import timezone
from app.models import ScheduledExam, Exam 

class ScheduledExamForm(forms.ModelForm):
    # Use an HTML5 datetime-local widget for a better UI
    scheduled_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Select a future date and time."
    )

    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ScheduledExam
        fields = ['exam', 'scheduled_datetime']
    
    def clean_scheduled_datetime(self):
        scheduled_datetime = self.cleaned_data.get('scheduled_datetime')
        if scheduled_datetime < timezone.now():
            raise forms.ValidationError("Scheduled time cannot be in the past.")
        return scheduled_datetime
