from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import *

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()
from django.contrib.auth.hashers import make_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

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
        fields = ['name', 'email', 'phone_number', 'gender']

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

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = '__all__'  # or list your fields explicitly

    def clean_questions(self):
        questions = self.cleaned_data.get('questions')
        if questions and questions.count() > 20:
            raise ValidationError("An exam cannot have more than 20 questions.")
        return questions


class ScheduledExamForm(forms.ModelForm):
    class Meta:
        model = ScheduledExam
        fields = ['exam', 'scheduled_datetime']
        widgets = {
            'scheduled_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }


class QuestionForm(forms.ModelForm):
    choices = forms.ModelMultipleChoiceField(
        queryset=Choice.objects.order_by("date_added"),  # Order choices
        widget=forms.CheckboxSelectMultiple,  # Optional: Display as checkboxes
    )
    class Meta:
        model = Question
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        choices = cleaned_data.get('choices')
        if choices and len(choices) > 4:
            raise ValidationError("A question can have max of 4 choices.")
        return cleaned_data
    