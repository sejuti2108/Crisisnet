from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Volunteer(models.Model):
    class Availability(models.TextChoices):
        AVAILABLE = "available", "Available for Deployment"
        DEPLOYED = "deployed", "Currently Deployed / On Duty"
        UNAVAILABLE = "unavailable", "Unavailable / On Leave"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="volunteer_profile",
        help_text="Linked user account for the volunteer",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Emergency contact phone number",
    )
    skills = models.CharField(
        max_length=255,
        default="General Relief Support",
        help_text="Specializations (e.g., First Aid, Rescue Operations, Logistics, Medical)",
    )
    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
        help_text="Current readiness / deployment status",
    )
    assigned_incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_volunteers",
        help_text="Active emergency incident this volunteer is currently assigned to",
    )
    assigned_shelter = models.ForeignKey(
        "shelters.Shelter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_volunteers",
        help_text="Relief shelter this volunteer is stationed at",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]
        verbose_name = "Volunteer"
        verbose_name_plural = "Volunteers"

    def clean(self):
        super().clean()
        # If marked unavailable, cannot have active deployments
        if self.availability == self.Availability.UNAVAILABLE:
            if self.assigned_incident or self.assigned_shelter:
                raise ValidationError(
                    "An unavailable volunteer cannot have active assignments. Clear incident and shelter first."
                )

    def save(self, *args, **kwargs):
        # Auto-update status when assigned or unassigned
        if self.assigned_incident or self.assigned_shelter:
            if self.availability != self.Availability.UNAVAILABLE:
                self.availability = self.Availability.DEPLOYED
        elif self.availability == self.Availability.DEPLOYED:
            self.availability = self.Availability.AVAILABLE

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def get_status_display(self):
        return self.get_availability_display()

    @property
    def is_available(self):
        return self.availability == self.Availability.AVAILABLE

    @property
    def is_deployed(self):
        return self.availability == self.Availability.DEPLOYED

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.get_availability_display()})"
