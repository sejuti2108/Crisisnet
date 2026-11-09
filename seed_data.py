import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crisisnet.settings")
django.setup()

from django.contrib.auth import get_user_model
from warehouses.models import Warehouse, InventoryItem
from shelters.models import Shelter
from incidents.models import Incident

User = get_user_model()

# Ensure an admin user exists
admin_user, created = User.objects.get_or_create(
    username="Anup",
    defaults={
        "email": "anupsrk2k4@gmail.com",
        "is_staff": True,
        "is_superuser": True,
        "role": User.Role.ADMIN,
    }
)
if created:
    admin_user.set_password("admin123")
    admin_user.save()
    print("Created superuser 'admin' with password 'admin123'")

# 1. Warehouses
warehouses_data = [
    {
        "name": "Dhaka Central Relief Warehouse",
        "latitude": 23.75,
        "longitude": 90.40,
        "items": [
            ("Water Purification Tablets", 5000, "boxes"),
            ("Emergency Rations (Dry Food)", 2000, "packs"),
            ("Medical First Aid Kits", 350, "kits"),
            ("Blankets & Tarpaulins", 1200, "pieces"),
        ]
    },
    {
        "name": "Chattogram Coastal Depot",
        "latitude": 22.34,
        "longitude": 91.82,
        "items": [
            ("Life Jackets", 600, "pieces"),
            ("Clean Drinking Water (5L)", 1500, "bottles"),
            ("Rice & Grains", 3000, "kg"),
        ]
    },
    {
        "name": "Sylhet Flood Relief Warehouse",
        "latitude": 24.89,
        "longitude": 91.86,
        "items": [
            ("Inflatable Rescue Boats", 15, "units"),
            ("Water Purification Kits", 2500, "kits"),
            ("High-Energy Biscuits", 4000, "packets"),
        ]
    },
]

for w_data in warehouses_data:
    wh, _ = Warehouse.objects.get_or_create(
        name=w_data["name"],
        defaults={"latitude": w_data["latitude"], "longitude": w_data["longitude"]},
    )
    for item_name, qty, unit in w_data["items"]:
        InventoryItem.objects.get_or_create(
            warehouse=wh,
            item_name=item_name,
            defaults={"quantity": qty, "unit": unit},
        )
print(f"Warehouses present: {Warehouse.objects.count()}")

# 2. Shelters
shelters_data = [
    {
        "name": "Rajshahi Central High School Shelter",
        "location": "Sadar, Rajshahi",
        "latitude": 24.40,
        "longitude": 88.58,
        "capacity": 500,
        "current_occupancy": 210,
        "status": Shelter.Status.OPEN,
    },
    {
        "name": "Sylhet Community College Shelter",
        "location": "Kotwali, Sylhet",
        "latitude": 24.90,
        "longitude": 91.87,
        "capacity": 350,
        "current_occupancy": 310,
        "status": Shelter.Status.OPEN,
    },
    {
        "name": "Cox's Bazar Multi-Purpose Cyclone Shelter",
        "location": "Kolatoli, Cox's Bazar",
        "latitude": 21.45,
        "longitude": 91.97,
        "capacity": 800,
        "current_occupancy": 780,
        "status": Shelter.Status.FULL,
    },
    {
        "name": "Dhaka Mirpur Emergency Relief Center",
        "location": "Mirpur-10, Dhaka",
        "latitude": 23.80,
        "longitude": 90.36,
        "capacity": 450,
        "current_occupancy": 150,
        "status": Shelter.Status.OPEN,
    },
]

for s_data in shelters_data:
    Shelter.objects.get_or_create(
        name=s_data["name"],
        defaults={
            "location": s_data["location"],
            "latitude": s_data["latitude"],
            "longitude": s_data["longitude"],
            "capacity": s_data["capacity"],
            "current_occupancy": s_data["current_occupancy"],
            "status": s_data["status"],
            "manager": admin_user,
        },
    )
print(f"Shelters present: {Shelter.objects.count()}")

# 3. Incidents (Fires & Floods)
incidents_data = [
    {
        "title": "Garment Factory Fire, Savar",
        "incident_type": Incident.IncidentType.FIRE,
        "severity": Incident.Severity.HIGH,
        "status": Incident.Status.ACTIVE,
        "location": "Savar Industrial Area, Dhaka",
        "latitude": 23.8583,
        "longitude": 90.2667,
        "description": "Industrial textile unit fire spreading due to stored fabric. Emergency fire services engaged.",
    },
    {
        "title": "Chemical Depot Fire, Sitakunda",
        "incident_type": Incident.IncidentType.FIRE,
        "severity": Incident.Severity.CRITICAL,
        "status": Incident.Status.ACTIVE,
        "location": "Sitakunda Container Depot, Chattogram",
        "latitude": 22.3569,
        "longitude": 91.7832,
        "description": "Toxic fume fire at chemical container facility. 1km exclusion perimeter established.",
    },
    {
        "title": "Residential Market Fire, Rajshahi",
        "incident_type": Incident.IncidentType.FIRE,
        "severity": Incident.Severity.MEDIUM,
        "status": Incident.Status.ACTIVE,
        "location": "Shaheb Bazar, Rajshahi",
        "latitude": 24.3745,
        "longitude": 88.6042,
        "description": "Electrical short circuit in market complex. Contained to second floor.",
    },
    {
        "title": "Surma River Flash Flood",
        "incident_type": Incident.IncidentType.FLOOD,
        "severity": Incident.Severity.CRITICAL,
        "status": Incident.Status.ACTIVE,
        "location": "Kanaighat & Gowainghat Upazilas, Sylhet",
        "latitude": 25.0100,
        "longitude": 92.0500,
        "description": "Severe flash flood inundating low-lying villages. Evacuations actively ongoing.",
    },
]

for inc_data in incidents_data:
    Incident.objects.get_or_create(
        title=inc_data["title"],
        defaults={
            "incident_type": inc_data["incident_type"],
            "severity": inc_data["severity"],
            "status": inc_data["status"],
            "location": inc_data["location"],
            "latitude": inc_data["latitude"],
            "longitude": inc_data["longitude"],
            "description": inc_data["description"],
            "reported_by": admin_user,
        },
    )
print(f"Incidents present: {Incident.objects.count()}")
print("Database seeding completed successfully.")
