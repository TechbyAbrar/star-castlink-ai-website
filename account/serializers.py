#account/serialziers.py
from rest_framework import serializers
from .models import UserAuth
from django.utils import timezone

from rest_framework import serializers
from django.contrib.auth.hashers import make_password

from django.contrib.auth import get_user_model
User = get_user_model()

from .utils import (
    generate_username,
    send_otp_email,
    generate_tokens_for_user,
    generate_otp,
    get_otp_expiry,
)

class UserInfoSerializer(serializers.ModelSerializer):
    profile_pic_url = serializers.SerializerMethodField()

    class Meta:
        model = UserAuth
        fields = (
            "user_id",
            "email",
            "phone",
            "username",
            "full_name",
            "role",
            "bio",
            "company",
            "website",
            "country",
            "city",
            "profile_pic_url",
            "is_verified",
            "is_active",
            "is_staff",
            "is_subscribed",
            "date_joined",
            "updated_at",
            "last_login",
        )
        read_only_fields = ["user_id", "is_verified", "is_active", "is_staff", "is_subscribed", "date_joined", "updated_at", "last_login"]

    def get_profile_pic_url(self, obj: UserAuth):
        if not obj.profile_pic:
            return None

        request = self.context.get("request")
        url = obj.profile_pic.url
        return request.build_absolute_uri(url) if request else url



class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6)

    # Optional fields (keep only what you want from frontend)
    phone = serializers.CharField(required=True, allow_null=True, allow_blank=True, max_length=15)
    full_name = serializers.CharField(required=True, max_length=255)
    role = serializers.CharField(required=True)
    company = serializers.CharField(required=True, allow_null=True, allow_blank=True, max_length=255)
    website = serializers.URLField(required=True, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=True, allow_null=True, allow_blank=True, max_length=100)
    city = serializers.CharField(required=True, allow_null=True, allow_blank=True, max_length=100)
    username = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=50)

    def validate(self, data):
        email = data["email"].lower().strip()
        data["email"] = email

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Email already registered."})

        phone = data.get("phone")
        if phone:
            phone = phone.strip()
            data["phone"] = phone
            if User.objects.filter(phone=phone).exists():
                raise serializers.ValidationError({"phone": "Phone already registered."})

        # Optional: validate role if your model has choices
        role = data.get("role")
        if role and role not in ["Agent", "Client"]:
            raise serializers.ValidationError({"role": "Invalid role. Use 'Agent' or 'Client'."})

        return data

    def create(self, validated_data):
        raw_password = validated_data.pop("password")

        # Generate username if missing
        if not validated_data.get("username"):
            validated_data["username"] = generate_username(validated_data["email"])

        user = User(**validated_data)
        user.password = make_password(raw_password)

        # OTP fields (match your model: otp + otp_expired_at)
        user.otp = generate_otp()
        user.otp_expired_at = get_otp_expiry(30)  # 30 minutes
        user.is_verified = False

        user.save()

        # Send OTP
        message = f"Your verification code is {user.otp}. It expires in 30 minutes."
        send_otp_email(user.email, message)

        return user



class VerifyOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(otp=data["otp"], otp_expired_at__gte=timezone.now())
        except User.DoesNotExist:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})

        if user.is_verified:
            raise serializers.ValidationError({"otp": "User already verified."})

        data["user"] = user
        return data

    def save(self, **kwargs):
        user = self.validated_data["user"]
        from django.db import transaction
        with transaction.atomic():
            user.is_verified = True
            user.otp = None
            user.otp_expired = None
            user.save(update_fields=["is_verified", "otp", "otp_expired_at"])
        return user


class ResendVerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "Email not registered."})

        if user.is_verified:
            raise serializers.ValidationError({"email": "User already verified."})

        data["user"] = user
        return data

    def save(self, **kwargs):
        user = self.validated_data["user"]

        # Generate new OTP
        user.otp = generate_otp()
        user.otp_expired_at = get_otp_expiry()
        user.save(update_fields=["otp", "otp_expired_at"])

        # Send SMS
        message = f"Your new verification code is {user.otp}. It expires in 30 minutes."
        send_otp_email(user.email, message)

        return user
    
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError({
                "email": "Email is required.",
                "password": "Password is required."
            })

        user = User.objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid credentials."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "This account is inactive."})

        attrs['user'] = user
        return attrs


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.only('email', 'otp', 'otp_expired_at').get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("user account not found.")

        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        user.set_otp()
        user.save(update_fields=['otp', 'otp_expired_at'])
        send_otp_email(user.email, user.otp)
        return user
    
    
    
class VerifyForgetPasswordOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, write_only=True)

    def validate_otp(self, value):
        try:
            user = User.objects.only(
                'user_id', 'email', 'otp', 'otp_expired_at', 'is_verified'
            ).get(otp=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP.")

        if not user.is_verified:
            raise serializers.ValidationError("user account is not verified. Please, verify your email first.")

        if user.otp_expired_at is None or user.otp_expired_at < timezone.now():
            raise serializers.ValidationError("OTP has expired.")

        self.context['user'] = user
        return value

    def create_access_token(self):
        user = self.context['user']
        tokens = generate_tokens_for_user(user)
        return tokens['access']

    def to_representation(self, instance):
        """Custom response after successful OTP verification."""
        user = self.context['user']
        return {
            "success": True,
            "message": "OTP verified successfully.",
            "access_token": self.create_access_token(),
            "user": {
                "user_id": user.user_id,
                "email": user.email,
            },
        }


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        new = attrs.get("new_password")
        confirm = attrs.get("confirm_password")

        if new != confirm:
            raise serializers.ValidationError("Passwords do not match.")

        user = self.context["request"].user
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("otp verification token required.")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user