from .models import *

def phone_or_email():
  username = ''
  user = request.user.objects.get(email=username) if '@' in username else request.user.objects.get(phone_number=username)

  if username == email:
    user.send_otp_email()  # Send OTP
    messages.success(request, 'OTP sent to your email. Verify your account.')
    return redirect('verify_otp', user_id=user.id)
  else:
    return redirect("home")

def set_price_and_duration(plan):
    price = 0
    duration = 0
    if plan == 'Daily':
        price = 500
        duration = 1
    elif plan == 'Weekly':
        price = 2000
        duration = 7
    elif plan == 'Monthly':
        price = 3500
        duration = 30
    else:
        price = 10000
        duration = None
    return price, duration