from django import forms
from django.core.exceptions import ValidationError
from requests_app.models import Request


class ShelterOccupancyUpdateForm(forms.Form):
    """Form for shelter managers to update live occupancy."""
    current_occupancy = forms.IntegerField(
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter current number of occupants",
        }),
    )

    def __init__(self, *args, shelter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.shelter = shelter
        if shelter:
            self.fields["current_occupancy"].initial = shelter.current_occupancy

    def clean_current_occupancy(self):
        occupancy = self.cleaned_data.get("current_occupancy")
        if self.shelter and occupancy > self.shelter.capacity:
            raise ValidationError(
                f"Occupancy ({occupancy}) cannot exceed maximum shelter capacity ({self.shelter.capacity})."
            )
        return occupancy


class ShelterSupplyRequestForm(forms.Form):
    """Form for shelter managers to submit resource/supply requests."""
    DEFAULT_ITEMS = [
        ("Drinking Water (Liters)", "Drinking Water (Liters)"),
        ("Rice (kg)", "Rice (kg)"),
        ("Blankets", "Blankets"),
        ("First Aid & Medical Kits", "First Aid & Medical Kits"),
        ("Dry Food Packs", "Dry Food Packs"),
        ("Tents / Tarpaulins", "Tents / Tarpaulins"),
        ("Baby Food / Milk", "Baby Food / Milk"),
        ("Sanitation Kits", "Sanitation Kits"),
    ]

    item_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., Blankets, Drinking Water, Rice (kg)",
            "list": "common_items_list",
        }),
        help_text="Choose a standard relief item or specify custom provisions.",
    )
    quantity = forms.IntegerField(
        min_value=1,
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Required quantity",
        }),
    )
