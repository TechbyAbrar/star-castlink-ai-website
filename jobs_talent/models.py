from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
# Create your models here.
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

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
            models.Index(fields=["agent"]),
            models.Index(fields=["is_available"]),
            models.Index(fields=["country"]),
            models.Index(fields=["gender"]),
        ]

    def __str__(self):
        return f"{self.name} (Talent #{self.talent_id})"
    
    