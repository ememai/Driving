from django.conf import settings
from app.models import UserProfile  # replace with your actual model path

def associate_by_email(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        return {'is_new': False, 'user': user}

    email = details.get('email')
    if not email:
        return

    try:
        user = UserProfile.objects.get(email=email)
        return {'is_new': False, 'user': user}
    except UserProfile.DoesNotExist:
        return  # Continue to create a new user


def save_user_names(backend, details, user=None, *args, **kwargs):
    if user:
        first_name = details.get('first_name', '')
        email = details.get('email', '')
        # Always ensure uniqueness, even if first_name is present
        if not first_name or first_name.strip() == '':
            if email:
                base_name = email.split('@')[0]
            else:
                base_name = f'user_{user.pk or "new"}'
        else:
            base_name = first_name.strip()
        unique_name = base_name
        counter = 1
       
        while UserProfile.objects.filter(name=unique_name).exclude(pk=user.pk).exists():
            unique_name = f"{base_name}{counter}"
            counter += 1
        user.name = unique_name if not user.name else user.name  # Only set if name is empty
        user.save()
