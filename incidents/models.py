from django.conf import settings
from django.db import models


class Incident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        REPORTED = "reported", "Reported"
        ACTIVE = "active", "Active / Ongoing"
        CONTAINED = "contained", "Contained"
        RESOLVED = "resolved", "Resolved"

    class IncidentType(models.TextChoices):
        FLOOD = "flood", "Flood"
        CYCLONE = "cyclone", "Cyclone"
        FIRE = "fire", "Fire Outbreak"
        LANDSLIDE = "landslide", "Landslide / Erosion"
        WATERLOGGING = "waterlogging", "Urban Waterlogging"
        EARTHQUAKE = "earthquake", "Earthquake"
        OTHER = "other", "Other Emergency"

    title = models.CharField(
        max_length=200,
        help_text="Short descriptive title of the emergency event",
    )
    incident_type = models.CharField(
        max_length=30,
        choices=IncidentType.choices,
        default=IncidentType.FLOOD,
        help_text="Category of disaster event",
    )
    description = models.TextField(
        help_text="Detailed assessment of situation, affected populations, and immediate hazards",
    )
    location = models.CharField(
        max_length=255,
        help_text="District, Upazila, or specific geographical area affected",
    )
    latitude = models.FloatField(
        default=23.8103,
        help_text="Center latitude coordinate of the disaster zone",
    )
    longitude = models.FloatField(
        default=90.4125,
        help_text="Center longitude coordinate of the disaster zone",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        help_text="Operational severity level",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current containment / operational lifecycle state",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_incidents",
        help_text="User who logged or created this incident report",
    )
    affected_shelters = models.ManyToManyField(
        "shelters.Shelter",
        blank=True,
        related_name="incidents",
        help_text="Shelters impacted or actively sheltering victims from this incident",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title} ({self.get_status_display()})"

    @property
    def is_active(self):
        return self.status in [self.Status.REPORTED, self.Status.ACTIVE]
