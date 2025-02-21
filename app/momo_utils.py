import requests
import logging
import re
import uuid
import base64
from django.conf import settings
from django.core.cache import cache

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define base URL
BASE_URL = settings.MTN_MOMO_BASE_URL


def format_phone_number(phone_number):
    """Validate and format phone numbers to MTN MoMo expected format."""
    phone_number = re.sub(r'\D', '', phone_number)  # Remove non-numeric characters

    # Check if it's already in international format (2507XXXXXXXX)
    if phone_number.startswith("250") and len(phone_number) == 12:
        return phone_number  # Already valid

    # Check if it's in local format (07XXXXXXXX)
    if phone_number.startswith("07") and len(phone_number) == 10:
        return f"25{phone_number}"  # Convert to international format

    return None  # Invalid number
 # Invalid phone number


def get_mtn_momo_token():
    """Retrieve and cache the MTN MoMo API token."""
    try:
        token = cache.get('mtn_momo_token')
        if token:
            return token

        url = f"{BASE_URL}/collection/token/"

        credentials = f"{settings.MTN_MOMO_API_USER_ID}:{settings.MTN_MOMO_API_KEY}"

        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            cache.set("mtn_momo_token", token, expires_in - 60)  # Cache it
            return token
        else:
            logging.error(f"Failed to get MoMo token: {response.text}")
            return None
    except requests.RequestException as e:
        logging.error(f"MoMo Token Request Failed: {e}")
        return None


def request_momo_payment(phone_number, amount):
    """Initiate a MoMo payment request."""
    try:
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            return {"error": "Invalid phone number format"}, None

        url = f"{BASE_URL}/collection/v1_0/requesttopay"
        transaction_id = str(uuid.uuid4())

        token = get_mtn_momo_token()
        if not token:
            return {"error": "Failed to retrieve API token"}, None

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": transaction_id,
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "amount": str(amount),
            "currency": "EUR",
            "externalId": transaction_id,
            "payer": {"partyIdType": "MSISDN", "partyId": formatted_phone},
            "payerMessage": "Payment for service",
            "payeeNote": "Thank you for your payment",
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in [200, 202]:  # Success
            return {"message": "Payment request sent"}, transaction_id
        
        logging.error(f"MoMo Payment Request Failed: {response.text}")
        return {"error": "Payment request failed"}, None
    except requests.RequestException as e:
        logging.error(f"MoMo Payment Request Exception: {e}")
        return {"error": "Network error while initiating payment"}, None


def check_payment_status(transaction_id):
    """Check the status of a MoMo payment."""
    if not transaction_id:
        return {"error": "Invalid transaction ID"}

    try:
        url = f"{BASE_URL}/collection/v1_0/requesttopay/{transaction_id}"
        token = get_mtn_momo_token()
        if not token:
            return {"error": "Failed to retrieve API token"}

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
        }

        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logging.error(f"Failed to check payment status: {response.text}")
            return {"error": "Failed to fetch payment status"}

        if not response.text.strip():
            return {"error": "Empty response from API"}

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            logging.error(f"Failed to parse JSON response: {response.text}")
            return {"error": "Invalid JSON response"}
    except requests.RequestException as e:
        logging.error(f"MoMo Payment Status Request Exception: {e}")
        return {"error": "Network error while checking payment status"}


