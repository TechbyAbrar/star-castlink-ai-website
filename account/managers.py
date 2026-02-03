from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .services import generate_username


class CustomUserManager(BaseUserManager):

    def _create_user(self, *, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email must be provided"))

        if not full_name:
            raise ValueError(_("Full name must be provided"))

        email = self.normalize_email(email)

        # Auto-generate username if missing
        if not extra_fields.get("username"):
            extra_fields["username"] = generate_username(email)

        with transaction.atomic():
            user = self.model(
                email=email,
                full_name=full_name,
                **extra_fields,
            )
            user.set_password(password)
            user.save(using=self._db)

        return user

    def create_user(self, *, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_verified", False)

        return self._create_user(
            email=email,
            full_name=full_name,
            password=password,
            **extra_fields,
        )

    def create_superuser(self, *, email, full_name, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True"))

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True"))

        return self._create_user(
            email=email,
            full_name=full_name,
            password=password,
            **extra_fields,
        )
