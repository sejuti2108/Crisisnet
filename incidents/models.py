from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
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

    class BuildingMaterial(models.TextChoices):
        CONCRETE = "concrete", "Concrete / Brick"
        TIN = "tin", "Tin / Corrugated Sheet"
        WOOD = "wood", "Wood / Timber"
        BAMBOO = "bamboo", "Bamboo / Thatch"

    class RoadAccess(models.TextChoices):
        WIDE_ROAD = "wide_road", "Wide Road"
        MEDIUM_ROAD = "medium_road", "Medium Road"
        NARROW_ALLEY = "narrow_alley", "Narrow Alley"

    class AreaDensity(models.TextChoices):
        LOW_DENSITY = "low_density", "Low Density"
        RESIDENTIAL = "residential", "Residential"
        HIGH_DENSITY = "high_density", "High Density"
        SLUM = "slum", "Slum / Informal Settlement"

    class OccupancyType(models.TextChoices):
        OTHER = "other", "Other"
        RESIDENTIAL = "residential", "Residential"
        INDUSTRIAL = "industrial", "Industrial Site"
        MALL = "mall", "Shopping Mall"
        GARMENT_FACTORY = "garment_factory", "Garment Factory"
        CHEMICAL = "chemical", "Chemical Facility"

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
    occupancy_type = models.CharField(
        max_length=30,
        choices=OccupancyType.choices,
        default=OccupancyType.OTHER,
        blank=True,
        help_text="Facility occupancy type (used for fire escalation scoring)",
    )
    building_material = models.CharField(
        max_length=20,
        choices=BuildingMaterial.choices,
        default=BuildingMaterial.CONCRETE,
        blank=True,
        help_text="Primary structural material (used for fire escalation scoring)",
    )
    road_access = models.CharField(
        max_length=20,
        choices=RoadAccess.choices,
        default=RoadAccess.MEDIUM_ROAD,
        blank=True,
        help_text="Fire-service road access width (used for fire escalation scoring)",
    )
    area_density = models.CharField(
        max_length=20,
        choices=AreaDensity.choices,
        default=AreaDensity.RESIDENTIAL,
        blank=True,
        help_text="Surrounding area density (used for fire escalation scoring)",
    )
    incident_hour = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text="Local outbreak hour (0-23); falls back to report creation hour if blank",
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

    def get_fire_assessment(self) -> dict | None:
        """Compute fire escalation risk via prediction.fire_severity for fire incidents."""
        if self.incident_type != self.IncidentType.FIRE:
            return None
        from django.utils import timezone
        from prediction.fire_severity import calculate_fire_severity

        if self.incident_hour is not None:
            hour = self.incident_hour
        elif self.created_at is not None:
            hour = timezone.localtime(self.created_at).hour
        else:
            hour = timezone.localtime(timezone.now()).hour

        return calculate_fire_severity(
            material=self.building_material or self.BuildingMaterial.CONCRETE,
            road_access=self.road_access or self.RoadAccess.MEDIUM_ROAD,
            density=self.area_density or self.AreaDensity.RESIDENTIAL,
            time_of_day=hour,
            occupancy_type=self.occupancy_type or self.OccupancyType.OTHER,
        )


class OperationalNotice(models.Model):
    class Priority(models.TextChoices):
        URGENT = "urgent", "Urgent / Critical Action"
        HIGH = "high", "High Priority"
        NORMAL = "normal", "Standard Operational Notice"
        ADVISORY = "advisory", "Advisory / Informational"

    title = models.CharField(
        max_length=200,
        help_text="Short headline of the operational directive or bulletin",
    )
    message = models.TextField(
        help_text="Full operational instructions, weather warning, or dispatch guidance",
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        help_text="Urgency level of this operational directive",
    )
    target_role = models.CharField(
        max_length=30,
        default="all",
        help_text="Intended audience (e.g. all, shelter_manager, volunteer, coordinator)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operational_notices",
        help_text="Authorized coordinator or admin issuing this broadcast",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Operational Notice"
        verbose_name_plural = "Operational Notices"

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title}"

