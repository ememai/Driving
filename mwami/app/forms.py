from django import forms

class SubscriptionForm(forms.Form):
    plan_choices = [
        ('monthly', 'Monthly - $10'),
        ('yearly', 'Yearly - $100'),
    ]
    plan = forms.ChoiceField(choices=plan_choices, widget=forms.RadioSelect)
