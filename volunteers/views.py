from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from incidents.models import Incident
from shelters.models import Shelter
from django.db.models import Q
from .forms import VolunteerAssignmentForm, VolunteerSelfUpdateForm
from .models import Volunteer


@role_required(User.Role.ADMIN, User.Role.COORDINATOR)
def volunteer_management(request):
    """
    Volunteer management page for Coordinators and Administrators:
    - Lists all volunteers with their availability and skills.
    - Allows assigning/reassigning volunteers to incidents and shelters.
    - Displays current deployment status and summary counts.
    """
    volunteers = Volunteer.objects.select_related(
        "user", "assigned_incident", "assigned_shelter"
    ).all()

    # Search & Filters
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status")
    incident_filter = request.GET.get("incident")
    shelter_filter = request.GET.get("shelter")

    if search_query:
        volunteers = volunteers.filter(
            Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(skills__icontains=search_query)
            | Q(phone__icontains=search_query)
        )
    if status_filter:
        volunteers = volunteers.filter(availability=status_filter)
    if incident_filter:
        volunteers = volunteers.filter(assigned_incident_id=incident_filter)
    if shelter_filter:
        volunteers = volunteers.filter(assigned_shelter_id=shelter_filter)

    total_count = Volunteer.objects.count()
    available_count = Volunteer.objects.filter(availability=Volunteer.Availability.AVAILABLE).count()
    deployed_count = Volunteer.objects.filter(availability=Volunteer.Availability.DEPLOYED).count()
    unavailable_count = Volunteer.objects.filter(availability=Volunteer.Availability.UNAVAILABLE).count()

    active_incidents = Incident.objects.filter(
        status__in=[Incident.Status.REPORTED, Incident.Status.ACTIVE]
    ).order_by("-created_at")
    active_shelters = Shelter.objects.filter(
        status__in=[Shelter.Status.OPEN, Shelter.Status.FULL]
    ).order_by("name")

    context = {
        "volunteers": volunteers,
        "total_count": total_count,
        "available_count": available_count,
        "deployed_count": deployed_count,
        "unavailable_count": unavailable_count,
        "active_incidents": active_incidents,
        "active_shelters": active_shelters,
        "status_choices": Volunteer.Availability.choices,
        "selected_status": status_filter,
        "selected_incident": incident_filter,
        "selected_shelter": shelter_filter,
        "search_query": search_query,
    }
    return render(request, "volunteers/volunteer_management.html", context)


@require_POST
@role_required(User.Role.ADMIN, User.Role.COORDINATOR)
def assign_volunteer(request, volunteer_id):
    """
    Handle volunteer deployment assignment or removal from an incident/shelter.
    Protected strictly against unauthorized users.
    """
    volunteer = get_object_or_404(Volunteer, id=volunteer_id)

    incident_id = request.POST.get("assigned_incident")
    shelter_id = request.POST.get("assigned_shelter")
    availability = request.POST.get("availability") or volunteer.availability

    # Conflict check: If volunteer is unavailable, cannot be assigned
    if availability == Volunteer.Availability.UNAVAILABLE and (incident_id or shelter_id):
        messages.error(
            request,
            f"Cannot assign volunteer '{volunteer.user.username}' while their status is marked Unavailable.",
        )
        return redirect("volunteer_management")

    # Update incident assignment
    if incident_id:
        incident = get_object_or_404(Incident, id=incident_id)
        volunteer.assigned_incident = incident
    else:
        volunteer.assigned_incident = None

    # Update shelter assignment
    if shelter_id:
        shelter = get_object_or_404(Shelter, id=shelter_id)
        volunteer.assigned_shelter = shelter
    else:
        volunteer.assigned_shelter = None

    volunteer.availability = availability
    volunteer.save()

    messages.success(
        request,
        f"Deployment details updated for volunteer '{volunteer.user.username}' ({volunteer.get_availability_display()}).",
    )
    return redirect("volunteer_management")


@role_required(User.Role.VOLUNTEER)
def volunteer_dashboard(request):
    """
    Volunteer personal operations dashboard showing their active assignments,
    incident and shelter details, and allowing status/contact updates.
    """
    volunteer, _ = Volunteer.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = VolunteerSelfUpdateForm(request.POST, instance=volunteer)
        if form.is_valid():
            form.save()
            messages.success(request, "Your readiness and contact details have been updated.")
            return redirect("dashboard_volunteer")
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        form = VolunteerSelfUpdateForm(instance=volunteer)

    context = {
        "volunteer": volunteer,
        "form": form,
        "assigned_incident": volunteer.assigned_incident,
        "assigned_shelter": volunteer.assigned_shelter,
    }
    return render(request, "volunteers/volunteer_dashboard.html", context)
