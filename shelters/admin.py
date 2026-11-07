from django.contrib import admin
from .models import Shelter


@admin.register(Shelter)
class ShelterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location",
        "capacity",
        "current_occupancy",
        "occupancy_percentage",
        "status",
        "manager",
        "updated_at",
    )
    list_filter = ("status", "manager")
    search_fields = ("name", "location", "manager__username", "manager__email")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at", "occupancy_percentage", "available_capacity")

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "location", "manager", "status"),
        }),
        ("Geospatial Location", {
            "fields": ("latitude", "longitude"),
        }),
        ("Capacity & Occupancy", {
            "fields": ("capacity", "current_occupancy", "available_capacity", "occupancy_percentage"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
