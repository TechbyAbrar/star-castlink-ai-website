from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .managers import CustomUserManager
from .utils import get_otp_expiry, validate_image
from .services import generate_otp


class UserAuth(AbstractBaseUser, PermissionsMixin):
    
    ROLE_CHOICES = [
        ('Agent', 'Agent'),
        ('Client', 'Client'),
    ]
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["is_active", "is_verified"]),
            models.Index(fields=["otp"]),
            models.Index(fields=["is_subscribed"]),
        ]

    user_id = models.BigAutoField(primary_key=True)

    email = models.EmailField(unique=True, max_length=255)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)

    full_name = models.CharField(max_length=255)
    profile_pic = models.ImageField(
        upload_to="profile/",
        # default="profile/profile.png",
        null=True,
        blank=True,
        validators=[validate_image],
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Client')
    
    bio = models.TextField(null=True, blank=True)
    
    company = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)

    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_expired_at = models.DateTimeField(null=True, blank=True)


    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    is_subscribed = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    def __str__(self) -> str:
        return self.email

    def set_otp(self, otp: str | None = None, expiry_minutes: int = 30) -> None:
        self.otp = otp or generate_otp()
        self.otp_expired_at = get_otp_expiry(expiry_minutes)
        self.save(update_fields=["otp", "otp_expired_at"])

    def is_otp_valid(self, otp: str) -> bool:
        return (
            self.otp == otp
            and self.otp_expired_at
            and timezone.now() <= self.otp_expired_at
        )

    def clear_otp(self) -> None:
        self.otp = None
        self.otp_expired_at = None
        self.save(update_fields=["otp", "otp_expired_at"])

    def get_full_name(self) -> str:
        return self.full_name
