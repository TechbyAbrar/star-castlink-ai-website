import secrets
import string
import logging
from typing import Any, Dict

from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken

try:
    import messagebird
except ImportError:
    messagebird = None

logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    return ''.join(secrets.choice("0123456789") for _ in range(length))

def generate_username(email: str) -> str:
    base = email.split("@")[0][:8]
    suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    return f"{base}{suffix}"


def send_email(subject: str, message: str, recipient_email: str) -> bool:
    from_email = getattr(settings, "EMAIL_HOST_USER", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None)
    if not from_email:
        raise RuntimeError("Sender email not configured")
    try:
        send_mail(subject=subject, message=message, from_email=from_email, recipient_list=[recipient_email], fail_silently=False)
        return True
    except BadHeaderError:
        logger.error("Invalid header sending email to %s", recipient_email)
        return False
    except Exception as e:
        logger.exception("Error sending email to %s: %s", recipient_email, e)
        return False


def send_otp_email(recipient_email: str, otp: str) -> bool:
    return send_email("Verify Your Email", f"Your OTP is: {otp}", recipient_email)


def send_sms(phone: str, message: str) -> bool:
    if not messagebird:
        logger.error("MessageBird not installed")
        return False
    try:
        client = messagebird.Client(settings.MESSAGEBIRD_API_KEY)
        response = client.message_create(
            originator=settings.DEFAULT_FROM_NUMBER,
            recipients=[phone],
            body=message
        )
        logger.info("SMS sent to %s: %s", phone, response.id)
        return True
    except messagebird.client.ErrorException as e:
        logger.error("MessageBird API error: %s", e.errors)
        return False
    except Exception as e:
        logger.exception("Unexpected SMS error for %s: %s", phone, e)
        return False


def send_otp_sms(phone: str, otp: str) -> bool:
    return send_sms(phone, f"Your OTP is: {otp}")


def generate_tokens_for_user(user: Any) -> Dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}



