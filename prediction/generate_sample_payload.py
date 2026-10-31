"""
Generate sample_payload.json for the map prototype.

The flood layer comes from the real prediction pipeline (manual overrides
plus seasonal-average fallback). Fire incidents, shelters and warehouses are
fake stand-ins until the Django backend supplies real records.

Run from the folder that contains manage.py:
    python -m prediction.generate_sample_payload
    python -m prediction.generate_sample_payload 7 (use July's averages)
"""

import json
import os
import sys

from .assemble_map_data import build_map_payload, get_shelter_flood_risk
from .fire_severity import calculate_fire_severity

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "map_prototype", "sample_payload.json")

# Admin-entered conditions for a few stations; every other station falls
# back to its seasonal average for the chosen month.
MANUAL_ENTRIES = {
    "Rajshahi": {"rainfall": 600, "relative_humidity": 85, "cloud_coverage": 6.5},
    "Sylhet": {"rainfall": 900, "relative_humidity": 90, "cloud_coverage": 7.2},
    "Dhaka": {"rainfall": 20, "relative_humidity": 40, "cloud_coverage": 3.5},
}

FIRE_CALLS = [
    {
        "incident_id": "fire_001",
        "name": "Garment factory, Savar",
        "lat": 23.8583,
        "lon": 90.2667,
        "inputs": {"material": "concrete", "road_access": "narrow_alley",
                   "density": "high_density", "time_of_day": 2,
                   "occupancy_type": "garment_factory"},
    },
    {
        "incident_id": "fire_002",
        "name": "Chemical storage, Chattogram",
        "lat": 22.3569,
        "lon": 91.7832,
        "inputs": {"material": "concrete", "road_access": "wide_road",
                   "density": "residential", "time_of_day": 14,
                   "occupancy_type": "chemical"},
    },
    {
        "incident_id": "fire_003",
        "name": "Residential cluster, Rajshahi",
        "lat": 24.3745,
        "lon": 88.6042,
        "inputs": {"material": "tin", "road_access": "medium_road",
                   "density": "residential", "time_of_day": 20,
                   "occupancy_type": "residential"},
    },
]

SHELTERS = [
    {"id": "shelter_001", "name": "Rajshahi Central Shelter", "lat": 24.40, "lon": 88.58},
    {"id": "shelter_002", "name": "Sylhet Community Shelter", "lat": 24.90, "lon": 91.87},
    {"id": "shelter_003", "name": "Cox's Bazar Cyclone Shelter", "lat": 21.45, "lon": 91.97},
]

WAREHOUSES = [
    {"id": "warehouse_001", "name": "Dhaka Relief Warehouse", "lat": 23.75, "lon": 90.40},
    {"id": "warehouse_002", "name": "Chattogram Relief Warehouse", "lat": 22.34, "lon": 91.82},
]


def with_flood_risk(site: dict, flood_zones: list[dict]) -> dict:
    """Attach the nearest station's flood risk to a shelter or warehouse."""
    risk = get_shelter_flood_risk(site["lat"], site["lon"], flood_zones)
    entry = dict(site)
    if risk:
        entry["nearest_station"] = risk["name"]
        entry["risk_label"] = risk.get("risk_label")
        entry["flood_probability"] = risk.get("flood_probability")
    return entry


def main() -> None:
    month = int(sys.argv[1]) if len(sys.argv) > 1 else None

    fire_incidents = []
    for call in FIRE_CALLS:
        result = calculate_fire_severity(**call["inputs"])
        fire_incidents.append({
            "incident_id": call["incident_id"],
            "name": call["name"],
            "lat": call["lat"],
            "lon": call["lon"],
            "occupancy_type": call["inputs"]["occupancy_type"],
            **result,
        })

    payload = build_map_payload(MANUAL_ENTRIES, fire_incidents, month)
    zones = payload["flood_risk_zones"]
    payload["shelters"] = [with_flood_risk(s, zones) for s in SHELTERS]
    payload["warehouses"] = [with_flood_risk(w, zones) for w in WAREHOUSES]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {OUTPUT_PATH}")
    print(f"  flood zones: {len(zones)}, fire incidents: {len(fire_incidents)}, "
          f"shelters: {len(payload['shelters'])}, warehouses: {len(payload['warehouses'])}")


if __name__ == "__main__":
    main()