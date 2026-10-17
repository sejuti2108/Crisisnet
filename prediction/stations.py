"""
Fixed list of the 33 weather stations/districts covered by the flood
prediction dataset. Each station has known coordinates and anchors the
flood risk map — shelters/warehouses inherit the risk of whichever
station is geographically nearest to them, rather than each location
getting its own live weather query (out of scope for this project).
"""

STATIONS = [
    {"name": "Barisal", "lat": 22.70, "lon": 90.3600},
    {"name": "Bhola", "lat": 22.70, "lon": 90.6600},
    {"name": "Bogra", "lat": 24.88, "lon": 89.3600},
    {"name": "Chandpur", "lat": 23.26, "lon": 90.6700},
    {"name": "Chittagong (City-Ambagan)", "lat": 22.35, "lon": 91.8166},
    {"name": "Chittagong (IAP-Patenga)", "lat": 22.34, "lon": 91.7900},
    {"name": "Comilla", "lat": 23.48, "lon": 91.1900},
    {"name": "Cox's Bazar", "lat": 21.46, "lon": 91.9800},
    {"name": "Dhaka", "lat": 23.78, "lon": 90.3900},
    {"name": "Dinajpur", "lat": 25.63, "lon": 88.6600},
    {"name": "Faridpur", "lat": 23.61, "lon": 89.8400},
    {"name": "Feni", "lat": 23.01, "lon": 91.3700},
    {"name": "Hatiya", "lat": 22.29, "lon": 91.1300},
    {"name": "Ishurdi", "lat": 24.12, "lon": 89.0400},
    {"name": "Jessore", "lat": 23.17, "lon": 89.2200},
    {"name": "Khepupara", "lat": 21.98, "lon": 90.2200},
    {"name": "Khulna", "lat": 22.80, "lon": 89.5800},
    {"name": "Kutubdia", "lat": 21.83, "lon": 91.8400},
    {"name": "Madaripur", "lat": 23.17, "lon": 90.1800},
    {"name": "Maijdee Court", "lat": 22.83, "lon": 91.0800},
    {"name": "Mongla", "lat": 22.43, "lon": 89.6600},
    {"name": "Mymensingh", "lat": 24.75, "lon": 90.4100},
    {"name": "Patuakhali", "lat": 22.36, "lon": 90.3400},
    {"name": "Rajshahi", "lat": 24.35, "lon": 88.5600},
    {"name": "Rangamati", "lat": 22.67, "lon": 92.2000},
    {"name": "Rangpur", "lat": 25.72, "lon": 89.2600},
    {"name": "Sandwip", "lat": 22.50, "lon": 91.4600},
    {"name": "Satkhira", "lat": 22.68, "lon": 89.0700},
    {"name": "Sitakunda", "lat": 22.64, "lon": 91.6400},
    {"name": "Srimangal", "lat": 24.29, "lon": 91.7300},
    {"name": "Sylhet", "lat": 24.88, "lon": 91.9300},
    {"name": "Tangail", "lat": 24.15, "lon": 89.5500},
    {"name": "Teknaf", "lat": 20.87, "lon": 92.2600},
]


def find_nearest_station(lat: float, lon: float) -> dict:
    """
    Given a coordinate (e.g. a shelter's location), return the geographically
    nearest station from the fixed list. Uses simple Euclidean distance on
    lat/lon — not geodesically precise, but more than accurate enough at
    this scale (station spacing is tens of km, not meters) and avoids
    pulling in a full geospatial library for one function.
    """
    def distance_sq(station):
        return (station["lat"] - lat) ** 2 + (station["lon"] - lon) ** 2

    return min(STATIONS, key=distance_sq)