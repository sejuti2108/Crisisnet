from django import forms

from .models import STATION_CHOICES


class WeatherOverrideForm(forms.Form):
    station_name = forms.ChoiceField(
        choices=STATION_CHOICES,
        label="Weather Station",
    )
    rainfall = forms.FloatField(
        min_value=0.0,
        label="Rainfall (mm)",
        help_text="Training range: 0–2072",
        widget=forms.NumberInput(attrs={"step": "0.1", "placeholder": "e.g. 600"}),
    )
    relative_humidity = forms.FloatField(
        min_value=0.0,
        max_value=100.0,
        label="Relative Humidity (%)",
        help_text="Valid: 0–100 (training range: 34–97)",
        widget=forms.NumberInput(attrs={"step": "0.1", "placeholder": "e.g. 85"}),
    )
    cloud_coverage = forms.FloatField(
        min_value=0.0,
        label="Cloud Coverage Index",
        help_text="Index (not %); training range: 0–7.9",
        widget=forms.NumberInput(attrs={"step": "0.1", "placeholder": "e.g. 6.5"}),
    )
