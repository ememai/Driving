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
        # Always ensure a non-empty base_name
        if first_name and first_name.strip():
            base_name = first_name.strip()
        elif email and email.split('@')[0].strip():
            base_name = email.split('@')[0].strip()
        else:
            base_name = f'user_{user.pk or "new"}'
        # Fallback to a default if still empty
        if not base_name:
            base_name = f'user_{user.pk or "new"}'
        unique_name = base_name
        counter = 1
        # Debug print to trace name assignment
        print(f"[DEBUG] Initial base_name: '{base_name}'")
        while not unique_name or UserProfile.objects.filter(name=unique_name).exclude(pk=user.pk).exists():
            unique_name = f"{base_name}{counter}"
            print(f"[DEBUG] Trying unique_name: '{unique_name}'")
            counter += 1
        print(f"[DEBUG] Final unique_name assigned: '{unique_name}'")
        user.name = unique_name
        user.save()
