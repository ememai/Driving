import requests
import logging
import re
import uuid
from django.conf import settings
import base64
from django.core.cache import cache


callback_url="https://545a-197-157-187-21.ngrok-free.app"

BASE_URL = settings.MTN_MOMO_BASE_URL



def format_phone_number(phone_number):
    """Validate and format phone numbers to MTN's expected format."""
    phone_number = re.sub(r'\D', '', phone_number)  # Remove non-numeric characters
    if phone_number.startswith("07") and len(phone_number) == 10:
        return f"25{phone_number}"  # Convert to international format for Rwanda
    return phone_number


def get_mtn_momo_token():
    token = cache.get('mtn_momo_token')
    if token:
        return token

    url = f"{BASE_URL}/collection/token/"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
        "Authorization": f"Basic {settings.MTN_MOMO_API_KEY}",
    }
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        cache.set("mtn_momo_token", token, expires_in - 60)  # Store token in cache
        return token
    return None


def request_momo_payment(phone_number, amount):
    try:
        url = f"{BASE_URL}/collection/v1_0/requesttopay"
        transaction_id = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {get_mtn_momo_token()}",
            "X-Reference-Id": transaction_id,
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "amount": str(amount),
            "currency": "RWF",
            "externalId": transaction_id,
            "payer": {"partyIdType": "MSISDN", "partyId": phone_number},
            "payerMessage": "Payment for service",
            "payeeNote": "Thank you for your payment",
        }
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in [200, 202]:  # Success cases
            return response.status_code, transaction_id
        return response.status_code, None
    except requests.RequestException as e:
        logging.error(f"MoMo Payment Request Failed: {e}")
        return None, None



def check_payment_status(transaction_id):
    url = f"{settings.MTN_MOMO_BASE_URL}/collection/v1_0/requesttopay/{transaction_id}"
    headers = {
        "Authorization": f"Bearer {get_mtn_momo_token()}",
        "X-Target-Environment": "sandbox",
        "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200 or not response.text.strip():
            return {"error": "Invalid or empty response from API"}

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {"error": "Failed to parse JSON response"}
