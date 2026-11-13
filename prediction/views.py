from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from warehouses.models import Warehouse
from shelters.models import Shelter
from incidents.models import Incident

from .assemble_map_data import build_map_payload, get_shelter_flood_risk


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
    return render(request, "prediction/map.html", {"data_url": reverse("prediction:map_data")})


@login_required
def map_data(request):
    payload = build_map_payload()  # seasonal averages until an admin weather-entry page exists
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
    for inc in Incident.objects.filter(incident_type=Incident.IncidentType.FIRE):
        label = (
            "High Escalation Risk" if inc.severity in [Incident.Severity.CRITICAL, Incident.Severity.HIGH]
            else ("Medium Escalation Risk" if inc.severity == Incident.Severity.MEDIUM else "Standard Risk")
        )
        score = 90 if inc.severity == Incident.Severity.CRITICAL else (75 if inc.severity == Incident.Severity.HIGH else 50)
        fire_list.append({
            "incident_id": f"fire_{inc.pk}",
            "name": inc.title,
            "lat": inc.latitude,
            "lon": inc.longitude,
            "occupancy_type": "industrial",
            "label": label,
            "score": score,
            "factors": {"Road access": 20, "Combined structural risk": 15},
            "floor_applied": inc.severity == Incident.Severity.CRITICAL,
        })
    payload["fire_incidents"] = fire_list

    return JsonResponse(payload)
