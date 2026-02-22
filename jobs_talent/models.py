from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

User = get_user_model()

#job model
class Job(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"
        
    job_id = models.AutoField(primary_key=True)

    job_created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jobs_created",
    )
    
    job_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="jobs_assigned",
        null=True, blank=True,
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Optional filters shown in UI
    location = models.CharField(max_length=255, blank=True)
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    job_type = models.CharField(max_length=120, blank=True)  # e.g. "Summer Fashion"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # If you want AI prompt tracking
    ai_prompt = models.TextField(blank=True)

    # Counters are optional; you can also compute them.
    applicants_count = models.PositiveIntegerField(default=0)
    shortlisted_count = models.PositiveIntegerField(default=0)
    selftapes_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_created_by"]),
            models.Index(fields=["job_assigned_to"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def clean(self):
        if self.budget_min and self.budget_max and self.budget_min > self.budget_max:
            raise ValidationError("budget_min cannot be greater than budget_max")
        
        


#talent mdoel
class Talent(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    talent_id = models.AutoField(primary_key=True)

    added_by_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="talents_created",
    )

    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True)

    dob = models.DateField(null=True, blank=True)

    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)

    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # cm
    bust = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)    # cm
    waist = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)   # cm
    hips = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)    # cm

    shoe_size = models.PositiveIntegerField(null=True, blank=True)

    eye_color = models.CharField(max_length=64, blank=True)
    hair_type = models.CharField(max_length=64, blank=True)
    hair_color = models.CharField(max_length=64, blank=True)
    skin_color = models.CharField(max_length=64, blank=True)

    location = models.CharField(max_length=255, blank=True)
    continent = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, blank=True)

    is_available = models.BooleanField(default=True)
    available_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["added_by_agent"]),
            models.Index(fields=["is_available"]),
            models.Index(fields=["country"]),
            models.Index(fields=["gender"]),
        ]

    def __str__(self):
        return f"{self.name} (Talent #{self.talent_id})"
    
#talent images

class TalentImage(models.Model):
    image_id = models.AutoField(primary_key=True)

    talent = models.ForeignKey(
        "Talent",
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(upload_to="talents/images/")
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["talent", "is_primary"]),
            models.Index(fields=["talent", "sort_order"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["talent"],
                condition=Q(is_primary=True),
                name="unique_primary_image_per_talent",
            )
        ]

    def clean(self):
        if self.sort_order < 0:
            raise ValidationError("sort_order must be >= 0")

    def __str__(self):
        # NOTE: for FK, Django auto provides `talent_id`
        return f"TalentImage(talent={self.talent_id}, primary={self.is_primary}, order={self.sort_order})"

    def save(self, *args, **kwargs):
        """
        - If it's the first image for this talent, auto-make it primary.
        - If saving with is_primary=True, unset previous primary safely.
        """
        with transaction.atomic():
            is_new = self.pk is None

            # auto-primary for first image
            if is_new and not TalentImage.objects.filter(talent=self.talent).exists():
                self.is_primary = True

            # if setting primary, unset others
            if self.is_primary:
                TalentImage.objects.filter(
                    talent=self.talent,
                    is_primary=True
                ).exclude(pk=self.pk).update(is_primary=False)

            super().save(*args, **kwargs)

    def set_as_primary(self):
        with transaction.atomic():
            TalentImage.objects.filter(talent=self.talent, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
            self.is_primary = True
            self.save(update_fields=["is_primary"])