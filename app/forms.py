from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import *  # Import all models

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()
from django.contrib.auth.hashers import make_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from django import forms
import os
from django.conf import settings
from django.core.exceptions import ValidationError

from .widgets import *

from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from django.db.models import Count
import phonenumbers
from django.utils import timezone
from datetime import timedelta


class ImageLabelMixin:
    def get_image_label(self, obj, label_field="definition", image_field="sign_image", max_height=50, max_width=100):
        label = getattr(obj, label_field, "")
        image_url = getattr(obj, image_field).url if getattr(obj, image_field, None) else ""
        return format_html(
            '''
             <img src="{}" style="max-height:{}px; max-width:{}px; margin:5px;">
            <span>{}</span> 
            
            ''',
            image_url, max_height, max_width, label
        )


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, max_length=255, min_length=4, required=True, label="Password")

    password2 = forms.CharField(widget=forms.PasswordInput, max_length=255, min_length=4,required=True, label="Confirm Password")

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={"placeholder": "Enter phone number (e.g., 788123456)"}),
    )

    
    class Meta:
        model = UserProfile 
        fields = ['name', 'email', 'phone_number']

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        email = cleaned_data.get("email")
        phone_number = cleaned_data.get("phone_number")

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        
        required_errors ={
            "name" : "Izina rirakenewe.",
            "password1" : "Ijambo banga rirakenewe.",
            "password2" : "Kwemeza ijambo banga birakenewe."
        }

        for key, error in required_errors.items():
            if not cleaned_data.get(key):
                self._errors[key] = self.error_class([error])          

        
        
        if email and UserProfile.objects.filter(email=email).exists():
            raise forms.ValidationError("Iyi email isanzweho.")

        if phone_number:
        #     phone_number = self.normalize_phone_number(phone_number)
            stripped_number = phone_number[4:]  # Remove '+250'
            if UserProfile.objects.filter(phone_number__endswith=stripped_number).exists():
                raise forms.ValidationError("Iyi telefone isanzweho.")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Ijambo banga rigomba gusa aho warishyize hose.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # Hash the password properly
        if commit:
            user.save()
        return user
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")

        if phone:
            # Remove spaces, dashes, and ensure it starts with +250
            phone = phone.replace(" ", "").replace("-", "")
            if not phone.startswith("+250"):
                phone = "+250" + phone.lstrip("0")  # Remove leading zero and add +250

            # Validate with `phonenumbers` library
            try:
                parsed_number = phonenumbers.parse(phone, "RW")
                if not phonenumbers.is_valid_number(parsed_number):
                    raise forms.ValidationError("Kurikiza nimero y'inyarwanda urg:7812345 cg 0781234567.")
            except phonenumbers.phonenumberutil.NumberParseException:
                raise forms.ValidationError("Telefone wayujuje nabi kurikiza urugero.")

        return phone


class LoginForm(forms.Form):
    username = forms.CharField(label="Email or Phone")
    password = forms.CharField(widget=forms.PasswordInput, label="Enter your password",
    max_length=50,
    min_length=4,
    required=True)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")

        if not username:
            raise forms.ValidationError("Imeyili cg telefone uzuza kimwe.")

        return cleaned_data



class ExamCreationForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['exam_type','schedule_hour', 'duration', 'is_active', 'for_scheduling']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show this for creation (not editing)
        if not self.instance.pk:
            # Get all question types that have questions
            question_types = ExamType.objects.annotate(
                num_questions=Count('question')
            ).filter(num_questions__gt=0).order_by('order')
            
            # Create a field for each question type
            for q_type in question_types:
                field_name = f'questions_{q_type.id}'
                self.fields[field_name] = forms.ModelMultipleChoiceField(
                    queryset=Question.objects.filter(question_type=q_type).order_by('order'),
                    required=False,
                    label=f"{q_type.name} Questions",
                    widget=forms.CheckboxSelectMultiple
                )

                # Pre-fill initial values when editing an exam
                if self.instance.pk:
                    self.fields[field_name].initial = self.instance.questions.filter(question_type=q_type)
    def save(self, commit=True):
        exam = super().save(commit=commit)
        if commit:
            self.save_m2m()  # This will handle the many-to-many saves
        return exam
    
    def _save_m2m(self):
        super()._save_m2m()
        exam = self.instance
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('questions_'):
                exam.questions.add(*value)


# class ExamForm(forms.ModelForm):
#     class Meta:
#         model = Exam
#         fields = ['exam_type', 'duration', 'is_active', 'for_scheduling']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         # Get all question types that have associated questions
#         question_types = ExamType.objects.annotate(
#             num_questions=Count('question')
#         ).filter(num_questions__gt=0).order_by('order')

#         for q_type in question_types:
#             field_name = f'questions_{q_type.id}'
#             self.fields[field_name] = forms.ModelMultipleChoiceField(
#                 queryset=Question.objects.filter(question_type=q_type).order_by('order'),
#                 required=False,
#                 label=f"{q_type.name} Questions",
#                 widget=forms.CheckboxSelectMultiple
#             )

#             # Pre-fill initial values when editing an exam
#             if self.instance.pk:
#                 self.fields[field_name].initial = self.instance.questions.filter(question_type=q_type)

#     def save(self, commit=True):
#         exam = super().save(commit=commit)

#         if commit:
#             exam.questions.clear()  # Remove old questions
#             for field_name, value in self.cleaned_data.items():
#                 if field_name.startswith('questions_'):
#                     exam.questions.add(*value)

#         return exam


class ScheduledExamForm(forms.ModelForm):
    class Meta:
        model = ScheduledExam
        fields = ['exam', 'scheduled_datetime']
       

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        two_days_ago = timezone.now() - timedelta(days=2)
        self.fields['exam'].queryset = Exam.objects.filter(
            for_scheduling=True,
            created_at__gte=two_days_ago
        )

class RoadSignAdminForm(forms.ModelForm):
    USE_EXISTING = 'existing'
    UPLOAD_NEW = 'upload'
    
    image_choice = forms.ChoiceField(
        choices=[
            (UPLOAD_NEW, 'Upload new image'),
            (USE_EXISTING, 'Select existing image')
        ],
        widget=forms.RadioSelect(attrs={'class': 'image-choice-radio'}),
        initial=UPLOAD_NEW,
        label="Image Selection Method"
    )
    
    existing_image = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'existing-image-radio'}),
        label="Select from existing images"
    )
    
    class Meta:
        model = RoadSign
        fields = '__all__' 
        widgets = {
            'sign_image': forms.ClearableFileInput(attrs={'class': 'upload-image-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['existing_image'].choices = self._get_existing_images()
        
        if self.instance and self.instance.pk and self.instance.sign_image:
            self.fields['image_choice'].initial = self.USE_EXISTING
            self.fields['existing_image'].initial = self.instance.sign_image.name
            self.fields['sign_image'].required = False

    def _get_existing_images(self):
        """Get all images from the upload directory with preview HTML"""
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'road_signs')
        images = []
        
        if os.path.exists(upload_dir):
            for filename in sorted(os.listdir(upload_dir)):
                if filename.lower().endswith(('.jpg', '.png', '.webp')):
                    filepath = os.path.join('road_signs', filename)
                    images.append((filepath, self._get_image_preview_html(filepath, filename)))
        
        return images

    # Rest of your methods remain the same...

    def _get_image_preview_html(self, filepath, filename):
        """Generate HTML for image preview with radio button"""
        return mark_safe(
            f'<div class="image-radio-item">'
            f'<img src="{settings.MEDIA_URL}{filepath}" '
            f'style="max-height: 50px; max-width: 100px; vertical-align: middle; margin-right: 10px;">'
            f'{filename}'
            f'</div>'
        )

    def clean(self):
        cleaned_data = super().clean()
        choice = cleaned_data.get('image_choice')
        
        # Clear validation errors that might have been set automatically
        self.errors.pop('sign_image', None)
        
        if choice == self.USE_EXISTING:
            existing_image = cleaned_data.get('existing_image')
            if not existing_image:
                raise ValidationError("Please select an existing image.")
            cleaned_data['sign_image'] = existing_image
        else:
            if not cleaned_data.get('sign_image'):
                raise ValidationError("Please upload an image.")
        
        return cleaned_data

    def full_clean(self):
        """Override to prevent automatic sign_image validation"""
        super().full_clean()
        # Remove any automatic required field validation for sign_image
        if 'sign_image' in self._errors and self.cleaned_data.get('image_choice') == self.USE_EXISTING:
            del self._errors['sign_image']


class QuestionForm(forms.ModelForm, ImageLabelMixin):
    remove_question_image = forms.BooleanField(
        required=False,
        label="Remove current question image",
        help_text="Check this to remove the image associated with the question."
    )

    class Meta:
        model = Question
        fields = [
            'question_text',
            'question_sign',
            'choice1_text', 'choice2_text', 'choice3_text', 'choice4_text',
            'choice1_sign', 'choice2_sign', 'choice3_sign', 'choice4_sign',
            'correct_choice', 'order'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'question_text_input', 'placeholder': 'Enter question text'}),
            'question_sign': forms.RadioSelect(attrs={'class': 'question-sign-radio hidden', 'data-choice': 'question'}),
            'choice1_text': forms.Textarea(attrs={'rows': 2, 'cols': 40, 'placeholder': 'Enter choice 1 text', 'class': 'choice-text'}),
            'choice2_text': forms.Textarea(attrs={'rows': 2, 'cols': 40, 'placeholder': 'Enter choice 2 text', 'class': 'choice-text'}),
            'choice3_text': forms.Textarea(attrs={'rows': 2, 'cols': 40, 'placeholder': 'Enter choice 3 text', 'class': 'choice-text'}),
            'choice4_text': forms.Textarea(attrs={'rows': 2, 'cols': 40, 'placeholder': 'Enter choice 4 text', 'class': 'choice-text'}),
            'choice1_sign': forms.RadioSelect(attrs={'class': 'choice-sign-radio hidden', 'data-choice': 'choice1'}),
            'choice2_sign': forms.RadioSelect(attrs={'class': 'choice-sign-radio hidden', 'data-choice': 'choice2'}),
            'choice3_sign': forms.RadioSelect(attrs={'class': 'choice-sign-radio hidden', 'data-choice': 'choice3'}),
            'choice4_sign': forms.RadioSelect(attrs={'class': 'choice-sign-radio hidden', 'data-choice': 'choice4'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add image label logic for signs
        for i in range(1, 5):
            sign_field = f'choice{i}_sign'
            if sign_field in self.fields:
                self.fields[sign_field].label_from_instance = lambda obj: self.get_image_label(
                    obj, label_field="definition", image_field="sign_image", max_height=50, max_width=50
                )
                self.fields[sign_field].widget.attrs.update({
                    'class': 'choice-sign-radio hidden',
                    'data-choice': f'choice{i}',
                    'style': 'display: none;',
                })
                self.fields[sign_field].label = mark_safe(
                    f'''
                    <strong>Choice {i} is image?</strong>
                    <button type="button" class="choose-image-btn" data-choice="choice{i}">Select from Images</button>
                    '''
                )
                self.fields[sign_field].empty_label = 'None'

        if 'question_sign' in self.fields:
            self.fields['question_sign'].label_from_instance = lambda obj: self.get_image_label(
                obj, label_field="definition", image_field="sign_image", max_height=30, max_width=30
            )
            self.fields['question_sign'].widget.attrs.update({
                'class': 'question-sign-radio hidden',
                'data-choice': 'question',
                'style': 'display: none;',
            })
            self.fields['question_sign'].label = mark_safe(
                '''
                <span class="image-label">Question has image?</span>
                <button type="button" class="choose-image-btn" data-choice="question">Select from Images</button>
                '''
            )
            self.fields['question_sign'].empty_label = None

    def clean(self):
        cleaned_data = super().clean()

        errors = {}
        for i in range(1, 5):
            text_field = f'choice{i}_text'
            sign_field = f'choice{i}_sign'
            has_text = bool(cleaned_data.get(text_field))
            has_sign = bool(cleaned_data.get(sign_field))

            if has_text and has_sign:
                errors[text_field] = f"Choice {i} cannot have both text and a sign."
                errors[sign_field] = f"Choice {i} cannot have both text and a sign."
            elif not has_text and not has_sign:
                errors[text_field] = f"Choice {i} must have either text or a sign."
                errors[sign_field] = f"Choice {i} must have either text or a sign."

        if errors:
            raise ValidationError(errors)

        correct_choice = cleaned_data.get('correct_choice')
        if correct_choice:
            if not cleaned_data.get(f'choice{correct_choice}_text') and not cleaned_data.get(f'choice{correct_choice}_sign'):
                raise ValidationError(f"Correct choice {correct_choice} must have valid text or a sign.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('remove_question_image'):
            instance.question_sign = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
