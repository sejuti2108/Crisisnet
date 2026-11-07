from django import forms
from django.core.exceptions import ValidationError
from incidents.models import Incident
from shelters.models import Shelter
from .models import Volunteer


class VolunteerAssignmentForm(forms.ModelForm):
    """
    Form used by Administrators and Coordinators to assign a volunteer
    to an active disaster incident and/or an emergency shelter.
    """
    class Meta:
        model = Volunteer
        fields = [
            "availability",
            "assigned_incident",
            "assigned_shelter",
            "phone",
            "skills",
        ]
        widgets = {
            "availability": forms.Select(attrs={"class": "form-control"}),
            "assigned_incident": forms.Select(attrs={"class": "form-control"}),
            "assigned_shelter": forms.Select(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., +8801700000000"}),
            "skills": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., First Aid, Rescue, Logistics"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prioritize active incidents in the dropdown
        self.fields["assigned_incident"].queryset = Incident.objects.filter(
            status__in=[Incident.Status.REPORTED, Incident.Status.ACTIVE]
        ).order_by("-created_at")
        self.fields["assigned_shelter"].queryset = Shelter.objects.filter(
            status__in=[Shelter.Status.OPEN, Shelter.Status.FULL]
        ).order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        availability = cleaned_data.get("availability")
        incident = cleaned_data.get("assigned_incident")
        shelter = cleaned_data.get("assigned_shelter")

        if availability == Volunteer.Availability.UNAVAILABLE:
            if incident or shelter:
                raise ValidationError(
                    "Cannot assign an unavailable volunteer. Please set status to Available or Deployed first."
                )

        return cleaned_data


class VolunteerSelfUpdateForm(forms.ModelForm):
    """
    Form used by volunteers themselves on their dashboard to update
    their readiness, emergency phone, and skills.
    Cannot change incident or shelter assignments.
    """
    class Meta:
        model = Volunteer
        fields = ["availability", "phone", "skills"]
        widgets = {
            "availability": forms.Select(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "skills": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_availability(self):
        new_avail = self.cleaned_data.get("availability")
        # If currently assigned to incident or shelter, cannot set unavailable without warning
        if new_avail == Volunteer.Availability.UNAVAILABLE:
            if self.instance.assigned_incident or self.instance.assigned_shelter:
                raise ValidationError(
                    "You are currently assigned to active duties. Please contact a Coordinator to be relieved before marking unavailable."
                )
        return new_avail
