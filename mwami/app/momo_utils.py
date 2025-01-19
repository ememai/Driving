import requests
import uuid
from django.conf import settings

BASE_URL = settings.MOMO_BASE_URL

def get_access_token():
    """Fetch access token from MTN MoMo API."""
    url = f"{BASE_URL}/collection/token/"
    headers = {
        "Authorization": f"Basic {settings.MOMO_AUTH_HEADER}",
        "Ocp-Apim-Subscription-Key": settings.MOMO_PRIMARY_KEY,
    }
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]

def request_payment(phone_number, amount, transaction_id, callback_url):
    """Request payment from a user using MTN MoMo."""
    access_token = get_access_token()
    url = f"{BASE_URL}/collection/v1_0/requesttopay"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Reference-Id": transaction_id,
        "X-Target-Environment": "sandbox",
        "Ocp-Apim-Subscription-Key": settings.MOMO_PRIMARY_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "amount": str(amount),
        "currency": "RWF",
        "externalId": transaction_id,
        "payer": {"partyIdType": "MSISDN", "partyId": phone_number},
        "payerMessage": "Subscription Payment",
        "payeeNote": "Thank you for subscribing!",
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.status_code == 202  # Status 202 means the request was accepted

def check_payment_status(transaction_id):
    """Check the status of a payment request."""
    access_token = get_access_token()
    url = f"{BASE_URL}/collection/v1_0/requesttopay/{transaction_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Target-Environment": "sandbox",
        "Ocp-Apim-Subscription-Key": settings.MOMO_PRIMARY_KEY,
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def generate_transaction_id():
    """Generate a unique transaction ID."""
    return str(uuid.uuid4())