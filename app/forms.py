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
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Q
import dns.resolver
from django.core.exceptions import ValidationError
import re
import dns.resolver

# Optional: configure DNS resolver timeout
resolver = dns.resolver.Resolver()
resolver.timeout = 3
resolver.lifetime = 3


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

def email_domain_exists(email):
    domain = email.split('@')[-1].lower()

    # List of known good providers to skip DNS check
    known_providers = [
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
        "protonmail.com", "aol.com", "live.com", "gmx.com"
    ]
    
    if domain in known_providers:
        return True
    
    try:
        # Try resolving MX record
        answers = resolver.resolve(domain, 'MX')
        return bool(answers)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout, dns.resolver.NoNameservers):
        return False

COMMON_WEAK_PASSWORDS = [
    "1234", "2345", "3456", "4567", "5678", "6789", "7890",
    "abcd", "bcde", "cdef", "qwerty", "asdf", "zxcv",
    "1111", "0000", "aaaa", "bbbb", "zzzz"
    ]

def is_sequential(password):
    """Check if characters are sequential (either increasing or decreasing)"""
    if len(password) < 2:
        return False
    increasing = all(ord(password[i]) + 1 == ord(password[i+1]) for i in range(len(password)-1))
    decreasing = all(ord(password[i]) - 1 == ord(password[i+1]) for i in range(len(password)-1))
    return increasing or decreasing

def validate_strong_password(value):
    # Repeated characters
    if len(set(value)) == 1:
        raise ValidationError("Ijambobanga ntirigomba kuba inyuguti zisa.")
    
    # Common weak patterns
    if value.lower() in COMMON_WEAK_PASSWORDS:
        raise ValidationError("Iri jambobanga riroshye cyane.")

    # Sequential patterns
    # if is_sequential(value.lower()):
    #     raise ValidationError("Password cannot be a simple sequence of characters.")

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        max_length=255,
        min_length=4,
        required=True,
        label="Ijambobanga",
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput,
        max_length=255,
        min_length=4,
        required=True,
        label="Subiramo Ijambobanga",
    )

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        label="Telefoni",
        widget=forms.TextInput(attrs={"placeholder": "Urugero: 78..."}),
    )

    class Meta:
        model = UserProfile
        fields = ['name', 'email', 'phone_number']

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            raise ValidationError("Uzuza izina rirakenewe!")
        # if name and UserProfile.objects.filter(name=name).exists():
        #     name += f'_{self.cleaned_data.get("phone_number")}'
        if name.isdigit():
            raise ValidationError("Izina ntirikwiye kuba imibare gusa.")
        if not re.match(r"^[A-Za-zÀ-ÿ0-9 '-]+$", name):
            raise ValidationError("Izina ryemewe rigomba kuba ririmo inyuguti gusa.") 
        if len(name) < 4:
            raise ValidationError("Andika byibuza inyuguti 4")
        return name

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and UserProfile.objects.filter(email=email).exists():
            raise ValidationError("Iyi email isanzweho*")
        if email and not email_domain_exists(email):
            raise ValidationError(
                f"Imeri '{email}' wanditse ntago ibaho. Ongera usuzume izina ryayo."
            )
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if phone:
            phone = phone.replace(" ", "").replace("-", "")
            if not phone.startswith("+250"):
                phone = "+250" + phone.lstrip("0")
            try:
                parsed = phonenumbers.parse(phone, "RW")
                if not phonenumbers.is_valid_number(parsed):
                    raise ValidationError("Kurikiza nimero y'inyarwanda urg: 78... cyangwa 078...")
            except phonenumbers.NumberParseException:
                raise ValidationError("Telefone wayujuje nabi. Kurikiza urugero!")
            if UserProfile.objects.filter(phone_number=phone).exists():
                login_link = mark_safe('<a href="/login" class="alert-link">Injira</a>')
                raise ValidationError(f"Iyi telefone '{phone}' isanzweho* yikoreshe winjira")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if not password1:
            self.add_error('password1', "Ijambobanga rirakenewe!")
        if not password2:
            self.add_error('password2', "Subiramo ijambobanga rirakenewe!")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Ijambo banga rigomba gusa aho warishyize hose.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class WhatsAppConsentForm(forms.Form):
    consent = forms.ChoiceField(
        choices=[('yes', 'Yego'), ('no', 'Oya')],
        widget=forms.RadioSelect,
        label="",
        required=True,
        initial='no',
        error_messages={
            'required': "Hitamo Yego cyangwa Oya!"
        }
    )
    
    whatsapp_number = forms.CharField(
        required=False,
        max_length=20,
        label="WhatsApp Number",
        widget=forms.TextInput(attrs={
            'placeholder': '+25078...',
            'class': 'form-control',
        }),
        
        
    )

    def clean(self):
        cleaned_data = super().clean()
        consent = cleaned_data.get("consent")
        whatsapp_number = cleaned_data.get('whatsapp_number')

        if not consent:
            raise forms.ValidationError("Hitamo Yego cg Oya")

        if consent == 'yes' and not whatsapp_number:
            raise forms.ValidationError("Telefone ya WhatsApp irakenewe.")

        return cleaned_data


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


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Ijambo ry’ibanga rishya",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "class": "form-control"}),
        max_length=255,
        min_length=4,
    )

    new_password2 = forms.CharField(
        label="Emeza ijambo ry’ibanga rishya",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "class": "form-control"}),
        max_length=255,
        min_length=4,
    )

    def clean(self):
        cleaned_data = self.cleaned_data  # ⚠️ Not calling `super().clean()`
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if not password1:
            self.add_error("new_password1", "Ijambo banga rirakenewe.")

        if not password2:
            self.add_error("new_password2", "Kwemeza ijambo banga birakenewe.")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Ijambo banga rigomba gusa aho warishyize hose.")

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

class ScheduleExamForm(forms.ModelForm):
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
            self.fields['question_sign'].empty_label = "None"

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


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['user','plan', 'super_subscription', 'price','updated']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'plan': forms.Select(attrs={'class': 'form-control'}),
            'super_subscription': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'updated': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }     

    # def clean(self):
    #     cleaned_data = super().clean()
    #     user = cleaned_data.get("user")
    #     instance = self.instance

    #     if user:
    #         # Check for existing subscription excluding the current instance (for updates)
    #         existing = Subscription.objects.filter(user=user).exclude(pk=instance.pk).first()
    #         if existing:
    #             # Instead of raising a ValidationError, we silently allow it
    #             self.cleaned_data['existing_instance'] = existing  # optional if you want to access later
    #     return cleaned_data


    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['user'].queryset = UserProfile.objects.all().order_by('-date_joined')
        
class PhoneOrEmailPasswordResetForm(PasswordResetForm):
    query = forms.CharField(
        label="Email cyangwa Numero ya telefone",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def get_users(self, query):
        return UserProfile.objects.filter(
            Q(email__iexact=query) | Q(phone_number__iexact=query),
            is_active=True
        )

    def clean(self):
        cleaned_data = super().clean()
        query = cleaned_data.get("query")

        users = self.get_users(query)

        if not users.exists():
            raise ValidationError("Nta mukiliya tubonye ukoresheje ayo makuru.")

        # Check if at least one user has email
        if not any(user.email for user in users):
            raise ValidationError("Uwo mukiliya nta email afite. Wavugana n’ubuyobozi kugira ngo uhindurirwe ijambo ry’ibanga.")

        self._valid_users = users
        return cleaned_data

    def save(self, *args, **kwargs):
        # Trick Django into working with our dynamic field
        self.cleaned_data['email'] = self.cleaned_data['query']
        return super().save(*args, **kwargs)