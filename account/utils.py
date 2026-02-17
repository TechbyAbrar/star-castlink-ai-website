# account/utils.py
from __future__ import annotations

import logging
import secrets
import string
from datetime import timedelta
from typing import Any, Dict, Optional

import jwt
import requests
from PIL import Image

from django.conf import settings
from django.core.mail import BadHeaderError, send_mail
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

try:
    import messagebird
except ImportError:  # pragma: no cover
    messagebird = None


logger = logging.getLogger(__name__)

# Image validation settings
MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "GIF"}

# External endpoints
GOOGLE_TOKENINFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo"
FACEBOOK_ME_URL = "https://graph.facebook.com/me"
MICROSOFT_ME_URL = "https://graph.microsoft.com/v1.0/me"


# ----------------------------
# OTP & time helpers
# ----------------------------
def get_otp_expiry(minutes: int = 30) -> timezone.datetime:
    return timezone.now() + timedelta(minutes=minutes)


def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_username(email: str) -> str:
    base = email.split("@")[0][:8]
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    return f"{base}{suffix}"


# ----------------------------
# Image validation
# ----------------------------
def validate_image(image: Any) -> None:
    """
    Validates uploaded image by size and format.

    Raises:
        ValueError: if image is invalid, too large, or unsupported format.
    """
    if image.size > MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image too large (max 3MB)")

    try:
        img = Image.open(image)
        img.verify()
        if img.format not in ALLOWED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format: {img.format}")
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid image file: {exc}") from exc


# ----------------------------
# Social token decoders
# ----------------------------
def decode_apple_token(identity_token: str) -> Optional[Dict[str, str]]:
    try:
        decoded = jwt.decode(identity_token, options={"verify_signature": False})
        email = decoded.get("email")
        if not email:
            return None
        return {
            "email": email,
            "full_name": decoded.get("name", email.split("@")[0]),
            "profile_pic_url": None,
        }
    except Exception:
        return None


def decode_google_token(id_token: str) -> Optional[Dict[str, str]]:
    try:
        res = requests.get(
            GOOGLE_TOKENINFO_URL,
            params={"id_token": id_token},
            timeout=3,
        )
        data = res.json()
        email = data.get("email")
        if not email:
            return None
        return {
            "email": email,
            "full_name": data.get("name", ""),
            "profile_pic_url": data.get("picture"),
        }
    except Exception:
        return None


def decode_facebook_token(access_token: str) -> Optional[Dict[str, Any]]:
    try:
        res = requests.get(
            FACEBOOK_ME_URL,
            params={"fields": "id,name,email", "access_token": access_token},
            timeout=3,
        )
        data = res.json()
        if "error" in data:
            return None
        return data
    except Exception:
        return None


def decode_microsoft_token(access_token: str) -> Optional[Dict[str, str]]:
    try:
        res = requests.get(
            MICROSOFT_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=3,
        )
        data = res.json()
        email = data.get("mail") or data.get("userPrincipalName")
        if not email:
            return None
        return {
            "email": email,
            "full_name": data.get("displayName", ""),
            "profile_pic_url": None,
        }
    except Exception:
        return None


# ----------------------------
# Email & SMS helpers
# ----------------------------
def send_email(subject: str, message: str, recipient_email: str) -> bool:
    from_email = getattr(settings, "EMAIL_HOST_USER", None) or getattr(
        settings, "DEFAULT_FROM_EMAIL", None
    )
    if not from_email:
        raise RuntimeError("Sender email not configured")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        return True
    except BadHeaderError:
        logger.error("Invalid header sending email to %s", recipient_email)
        return False
    except Exception as exc:
        logger.exception("Error sending email to %s: %s", recipient_email, exc)
        return False


def send_otp_email(recipient_email: str, otp: str) -> bool:
    return send_email(
        subject="Verify Your Email",
        message=f"Your OTP is: {otp}",
        recipient_email=recipient_email,
    )


def send_sms(phone: str, message: str) -> bool:
    if not messagebird:
        logger.error("MessageBird not installed")
        return False

    try:
        client = messagebird.Client(settings.MESSAGEBIRD_API_KEY)
        response = client.message_create(
            originator=settings.DEFAULT_FROM_NUMBER,
            recipients=[phone],
            body=message,
        )
        logger.info("SMS sent to %s: %s", phone, response.id)
        return True
    except messagebird.client.ErrorException as exc:  # type: ignore[attr-defined]
        logger.error("MessageBird API error: %s", exc.errors)
        return False
    except Exception as exc:
        logger.exception("Unexpected SMS error for %s: %s", phone, exc)
        return False


def send_otp_sms(phone: str, otp: str) -> bool:
    return send_sms(phone, f"Your OTP is: {otp}")


# ----------------------------
# JWT helpers
# ----------------------------
def generate_tokens_for_user(user: Any) -> Dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}
