from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .stations import STATIONS

STATION_CHOICES = [(s["name"], s["name"]) for s in STATIONS]


class WeatherOverride(models.Model):
    station_name = models.CharField(
        max_length=100,
        unique=True,
        choices=STATION_CHOICES,
        help_text="Meteorological station to override with manual/live readings",
    )
    rainfall = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Rainfall (mm); training data range: 0–2072",
    )
    relative_humidity = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Relative humidity (%); valid range: 0–100",
    )
    cloud_coverage = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Cloud coverage index (not %); training data range: 0–7.9",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weather_overrides",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["station_name"]
        verbose_name = "Weather Override"
        verbose_name_plural = "Weather Overrides"

    def __str__(self):
        return f"{self.station_name} (Rain: {self.rainfall}, RH: {self.relative_humidity}%, Cloud: {self.cloud_coverage})"
