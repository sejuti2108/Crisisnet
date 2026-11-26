from django.contrib import admin

from .models import WeatherOverride


@admin.register(WeatherOverride)
class WeatherOverrideAdmin(admin.ModelAdmin):
    list_display = ("station_name", "rainfall", "relative_humidity", "cloud_coverage", "updated_by", "updated_at")
    search_fields = ("station_name",)
    readonly_fields = ("updated_at",)
