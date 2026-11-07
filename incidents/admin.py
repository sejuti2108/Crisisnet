from django.contrib import admin
from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "incident_type",
        "severity",
        "status",
        "location",
        "reported_by",
        "created_at",
    )
    list_filter = ("severity", "status", "incident_type", "created_at")
    search_fields = ("title", "description", "location")
    filter_horizontal = ("affected_shelters",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Incident Overview", {
            "fields": ("title", "incident_type", "description", "reported_by"),
        }),
        ("Location & Coordinates", {
            "fields": ("location", "latitude", "longitude"),
        }),
        ("Urgency & Status", {
            "fields": ("severity", "status"),
        }),
        ("Affected Facilities", {
            "fields": ("affected_shelters",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
