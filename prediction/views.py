from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from incidents.models import Incident
from shelters.models import Shelter
from warehouses.models import Warehouse

from .assemble_map_data import build_map_payload, get_shelter_flood_risk
from .flood_model import predict_flood_risk
from .forms import WeatherOverrideForm
from .models import WeatherOverride


def _with_flood_risk(site: dict, flood_zones: list[dict]) -> dict:
    """Attach the nearest weather station's flood risk to a shelter or warehouse."""
    risk = get_shelter_flood_risk(site["lat"], site["lon"], flood_zones)
    if risk:
        site["nearest_station"] = risk["name"]
        site["risk_label"] = risk.get("risk_label")
        site["flood_probability"] = risk.get("flood_probability")
    return site


@login_required
def map_page(request):
    can_override_weather = request.user.is_superuser or request.user.role in (
        User.Role.ADMIN,
        User.Role.COORDINATOR,
    )
    return render(
        request,
        "prediction/map.html",
        {
            "data_url": reverse("prediction:map_data"),
            "can_override_weather": can_override_weather,
        },
    )


@login_required
def map_data(request):
    manual_entries = {
        w.station_name: {
            "rainfall": w.rainfall,
            "relative_humidity": w.relative_humidity,
            "cloud_coverage": w.cloud_coverage,
        }
        for w in WeatherOverride.objects.all()
    }
    payload = build_map_payload(manual_entries=manual_entries)
    zones = payload["flood_risk_zones"]

    payload["warehouses"] = [
        _with_flood_risk(
            {"id": f"warehouse_{w.pk}", "name": w.name, "lat": w.latitude, "lon": w.longitude},
            zones,
        )
        for w in Warehouse.objects.all()
    ]
    payload["shelters"] = [
        _with_flood_risk(
            {"id": f"shelter_{s.pk}", "name": s.name, "lat": s.latitude, "lon": s.longitude},
            zones,
        )
        for s in Shelter.objects.all()
    ]

    fire_list = []
    other_list = []
    active_incidents = Incident.objects.exclude(status=Incident.Status.RESOLVED)

    for inc in active_incidents:
        if inc.incident_type == Incident.IncidentType.FIRE:
            assessment = inc.get_fire_assessment()
            if assessment is None:
                continue
            fire_list.append({
                "incident_id": f"fire_{inc.pk}",
                "name": inc.title,
                "lat": inc.latitude,
                "lon": inc.longitude,
                "occupancy_type": inc.occupancy_type or Incident.OccupancyType.OTHER,
                "url": f"/incidents/{inc.pk}/",
                **assessment,
            })
        else:
            other_list.append({
                "incident_id": f"incident_{inc.pk}",
                "name": inc.title,
                "incident_type": inc.incident_type,
                "incident_type_display": inc.get_incident_type_display(),
                "severity": inc.severity,
                "severity_display": inc.get_severity_display(),
                "status": inc.status,
                "status_display": inc.get_status_display(),
                "location": inc.location,
                "lat": inc.latitude,
                "lon": inc.longitude,
                "url": f"/incidents/{inc.pk}/",
            })

    payload["fire_incidents"] = fire_list
    payload["other_incidents"] = other_list

    return JsonResponse(payload)


@role_required(User.Role.ADMIN, User.Role.COORDINATOR)
def weather_overrides(request):
    """Manage live/manual station weather overrides for flood risk prediction."""
    if request.method == "POST":
        form = WeatherOverrideForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            override, created = WeatherOverride.objects.update_or_create(
                station_name=cd["station_name"],
                defaults={
                    "rainfall": cd["rainfall"],
                    "relative_humidity": cd["relative_humidity"],
                    "cloud_coverage": cd["cloud_coverage"],
                    "updated_by": request.user,
                },
            )
            pred = predict_flood_risk(
                rainfall=override.rainfall,
                relative_humidity=override.relative_humidity,
                cloud_coverage=override.cloud_coverage,
            )
            verb = "set" if created else "updated"
            messages.success(
                request,
                f"Live weather override {verb} for {override.station_name} "
                f"(Flood risk: {pred['risk_label']}, {round(pred['flood_probability'] * 100)}%).",
            )
            return redirect("prediction:weather_overrides")
    else:
        initial = {}
        station = request.GET.get("station")
        if station:
            initial["station_name"] = station
        form = WeatherOverrideForm(initial=initial)

    rows = []
    for ov in WeatherOverride.objects.select_related("updated_by").all():
        pred = predict_flood_risk(
            rainfall=ov.rainfall,
            relative_humidity=ov.relative_humidity,
            cloud_coverage=ov.cloud_coverage,
        )
        rows.append({"override": ov, "prediction": pred})

    return render(
        request,
        "prediction/weather_overrides.html",
        {"form": form, "rows": rows},
    )


@require_POST
@role_required(User.Role.ADMIN, User.Role.COORDINATOR)
def reset_weather_override(request, override_id):
    """Delete a station override so it reverts to its monthly seasonal baseline."""
    override = get_object_or_404(WeatherOverride, pk=override_id)
    station_name = override.station_name
    override.delete()
    messages.success(request, f"{station_name} reset to seasonal baseline.")
    return redirect("prediction:weather_overrides")
