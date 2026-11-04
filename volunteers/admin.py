from django.contrib import admin
from .models import Volunteer


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone",
        "skills",
        "availability",
        "assigned_incident",
        "assigned_shelter",
        "updated_at",
    )
    list_filter = ("availability", "assigned_incident", "assigned_shelter")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "phone",
        "skills",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("User & Contact", {
            "fields": ("user", "phone", "skills"),
        }),
        ("Readiness & Deployment", {
            "fields": ("availability", "assigned_incident", "assigned_shelter"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
