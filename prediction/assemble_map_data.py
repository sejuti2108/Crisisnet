from datetime import datetime, timezone

from .flood_model import predict_flood_risk
from .seasonal_averages import get_seasonal_average
from .stations import STATIONS, find_nearest_station


def resolve_station_weather(station_name: str, month: int, manual_entries: dict) -> dict | None:
    """Manual entry wins; otherwise seasonal average; otherwise None."""
    if station_name in manual_entries:
        return manual_entries[station_name]
    return get_seasonal_average(station_name, month)


def assemble_flood_risk_zones(manual_entries: dict | None = None, month: int | None = None) -> list[dict]:
    """Run flood prediction for each of the 33 stations."""
    manual_entries = manual_entries or {}
    month = month or datetime.now().month

    results = []
    for station in STATIONS:
        name = station["name"]
        weather = resolve_station_weather(name, month, manual_entries)
        if weather is None:
            continue

        entry = {
            "location_id": name.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            "name": name,
            "lat": station["lat"],
            "lon": station["lon"],
            "data_source": "manual" if name in manual_entries else "seasonal_average",
        }

        try:
            entry.update(
                predict_flood_risk(
                    rainfall=weather["rainfall"],
                    relative_humidity=weather["relative_humidity"],
                    cloud_coverage=weather["cloud_coverage"],
                )
            )
        except (ValueError, KeyError) as e:
            entry["error"] = str(e)

        results.append(entry)

    return results


def get_shelter_flood_risk(shelter_lat: float, shelter_lon: float, flood_risk_zones: list[dict]) -> dict | None:
    """Return the risk entry of the station nearest to the given coordinates."""
    if not flood_risk_zones:
        return None
    nearest_name = find_nearest_station(shelter_lat, shelter_lon)["name"]
    for entry in flood_risk_zones:
        if entry["name"] == nearest_name:
            return entry
    return None


def build_map_payload(
    manual_entries: dict | None = None,
    fire_incidents: list[dict] | None = None,
    month: int | None = None,
) -> dict:
    """Assemble the full map payload for the frontend."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "flood_risk_zones": assemble_flood_risk_zones(manual_entries, month),
        "fire_incidents": fire_incidents or [],
    }


if __name__ == "__main__":
    import json

    manual = {"Rajshahi": {"rainfall": 600, "relative_humidity": 85, "cloud_coverage": 6.5}}
    payload = build_map_payload(manual)
    print(f"Stations in payload: {len(payload['flood_risk_zones'])}")
    print(json.dumps(payload["flood_risk_zones"][:2], indent=2))