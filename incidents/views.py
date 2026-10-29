from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from requests_app.models import Request
from .models import Incident


@login_required
def incident_list(request):
    """List of reported emergency incidents with filtering and overview statistics."""
    incidents = Incident.objects.prefetch_related("affected_shelters").all()

    # Filtering
    status_filter = request.GET.get("status")
    severity_filter = request.GET.get("severity")
    type_filter = request.GET.get("type")

    if status_filter:
        incidents = incidents.filter(status=status_filter)
    if severity_filter:
        incidents = incidents.filter(severity=severity_filter)
    if type_filter:
        incidents = incidents.filter(incident_type=type_filter)

    total_active = Incident.objects.filter(
        status__in=[Incident.Status.REPORTED, Incident.Status.ACTIVE]
    ).count()
    critical_count = Incident.objects.filter(
        severity=Incident.Severity.CRITICAL,
        status__in=[Incident.Status.REPORTED, Incident.Status.ACTIVE],
    ).count()

    context = {
        "incidents": incidents,
        "total_active": total_active,
        "critical_count": critical_count,
        "status_choices": Incident.Status.choices,
        "severity_choices": Incident.Severity.choices,
        "type_choices": Incident.IncidentType.choices,
        "selected_status": status_filter,
        "selected_severity": severity_filter,
        "selected_type": type_filter,
    }
    return render(request, "incidents/incident_list.html", context)


@login_required
def incident_detail(request, incident_id):
    """
    Detailed incident view displaying location, severity, status,
    affected shelters, connected supply request history, and volunteer deployments.
    """
    incident = get_object_or_404(
        Incident.objects.prefetch_related("affected_shelters"),
        id=incident_id,
    )

    affected_shelters = incident.affected_shelters.all()
    affected_shelter_names = [s.name for s in affected_shelters]

    # Query connected supply requests from existing Request model
    connected_requests = []
    if affected_shelter_names:
        connected_requests = Request.objects.filter(
            shelter_name__in=affected_shelter_names
        ).order_by("-created_at")

    # Gracefully fetch assigned volunteers (Phase 6 model integration)
    assigned_volunteers = []
    if hasattr(incident, "volunteers"):
        assigned_volunteers = incident.volunteers.all()
    elif hasattr(incident, "assigned_volunteers"):
        assigned_volunteers = incident.assigned_volunteers.all()

    # Permission check for modification
    can_modify = (
        request.user.is_superuser
        or request.user.role in [User.Role.ADMIN, User.Role.COORDINATOR]
        or incident.reported_by == request.user
    )

    # Compute aggregate shelter metrics
    total_shelter_capacity = sum(s.capacity for s in affected_shelters)
    total_shelter_occupancy = sum(s.current_occupancy for s in affected_shelters)

    context = {
        "incident": incident,
        "affected_shelters": affected_shelters,
        "connected_requests": connected_requests,
        "assigned_volunteers": assigned_volunteers,
        "can_modify": can_modify,
        "total_shelter_capacity": total_shelter_capacity,
        "total_shelter_occupancy": total_shelter_occupancy,
        "status_choices": Incident.Status.choices,
        "severity_choices": Incident.Severity.choices,
    }
    return render(request, "incidents/incident_detail.html", context)


@require_POST
@login_required
def update_incident_status(request, incident_id):
    """
    Enforces authorization: only Admins, Coordinators, or the reporting user
    may modify incident severity and status.
    """
    incident = get_object_or_404(Incident, id=incident_id)

    can_modify = (
        request.user.is_superuser
        or request.user.role in [User.Role.ADMIN, User.Role.COORDINATOR]
        or incident.reported_by == request.user
    )

    if not can_modify:
        raise PermissionDenied("You do not have permission to modify this incident.")

    new_status = request.POST.get("status")
    new_severity = request.POST.get("severity")

    if new_status and new_status in dict(Incident.Status.choices):
        incident.status = new_status

    if new_severity and new_severity in dict(Incident.Severity.choices):
        incident.severity = new_severity

    incident.save(update_fields=["status", "severity", "updated_at"])
    messages.success(
        request,
        f"Incident '{incident.title}' updated: Status is now {incident.get_status_display()}, Severity is {incident.get_severity_display()}.",
    )
    return redirect("incident_detail", incident_id=incident.id)
