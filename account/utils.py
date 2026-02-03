from datetime import timedelta
from typing import Any, Dict, Optional

import jwt
import requests
from PIL import Image
from django.utils import timezone


def get_otp_expiry(minutes: int = 30) -> timezone.datetime:
    return timezone.now() + timedelta(minutes=minutes)


def validate_image(image: Any) -> None:
    max_size = 3 * 1024 * 1024
    allowed_formats = {"JPEG", "PNG", "GIF"}
    if image.size > max_size:
        raise ValueError("Image too large (max 3MB)")
    try:
        img = Image.open(image)
        img.verify()
        if img.format not in allowed_formats:
            raise ValueError(f"Unsupported image format: {img.format}")
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid image file: {e}")


def decode_apple_token(identity_token: str) -> Optional[Dict[str, str]]:
    try:
        decoded = jwt.decode(identity_token, options={"verify_signature": False})
        email = decoded.get("email")
        if not email:
            return None
        return {"email": email, "full_name": decoded.get("name", email.split("@")[0]), "profile_pic_url": None}
    except Exception:
        return None


def decode_google_token(id_token: str) -> Optional[Dict[str, str]]:
    try:
        data = requests.get(
            f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={id_token}", timeout=3
        ).json()
        if "email" not in data:
            return None
        return {"email": data.get("email"), "full_name": data.get("name", ""), "profile_pic_url": data.get("picture")}
    except Exception:
        return None


def decode_facebook_token(access_token: str) -> Optional[Dict[str, Any]]:
    try:
        data = requests.get(
            f"https://graph.facebook.com/me?fields=id,name,email&access_token={access_token}", timeout=3
        ).json()
        if "error" in data:
            return None
        return data
    except Exception:
        return None


def decode_microsoft_token(access_token: str) -> Optional[Dict[str, str]]:
    try:
        res = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=3
        ).json()
        email = res.get("mail") or res.get("userPrincipalName")
        if not email:
            return None
        return {"email": email, "full_name": res.get("displayName", ""), "profile_pic_url": None}
    except Exception:
        return None
