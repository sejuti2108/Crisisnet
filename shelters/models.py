from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Shelter(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open / Available"
        FULL = "full", "At Full Capacity"
        CLOSED = "closed", "Closed / Inactive"

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Official name of the emergency shelter",
    )
    location = models.CharField(
        max_length=255,
        help_text="Physical address or district/upazila location",
    )
    latitude = models.FloatField(
        default=23.8103,
        help_text="Geographical latitude coordinate",
    )
    longitude = models.FloatField(
        default=90.4125,
        help_text="Geographical longitude coordinate",
    )
    capacity = models.PositiveIntegerField(
        default=100,
        help_text="Total maximum accommodation capacity",
    )
    current_occupancy = models.PositiveIntegerField(
        default=0,
        help_text="Current number of sheltered individuals",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_shelters",
        help_text="Assigned Shelter Manager user account",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Shelter"
        verbose_name_plural = "Shelters"

    def clean(self):
        super().clean()
        if self.current_occupancy > self.capacity:
            raise ValidationError(
                {"current_occupancy": "Current occupancy cannot exceed total shelter capacity."}
            )

    @property
    def available_capacity(self):
        return max(0, self.capacity - self.current_occupancy)

    @property
    def occupancy_percentage(self):
        if self.capacity <= 0:
            return 0
        return round((self.current_occupancy / self.capacity) * 100, 1)

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status != self.Status.CLOSED:
            if self.current_occupancy >= self.capacity:
                self.status = self.Status.FULL
            elif self.status == self.Status.FULL and self.current_occupancy < self.capacity:
                self.status = self.Status.OPEN
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.current_occupancy}/{self.capacity}) - {self.get_status_display()}"
