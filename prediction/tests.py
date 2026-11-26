from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from crisisnet.asgi import application
from incidents.models import Incident
from prediction.assemble_map_data import build_map_payload, get_shelter_flood_risk
from prediction.fire_severity import calculate_fire_severity
from prediction.flood_model import predict_flood_risk
from prediction.models import WeatherOverride
from prediction.stations import STATIONS, find_nearest_station
from shelters.models import Shelter

User = get_user_model()


class WeatherOverrideViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ValidPass123!"
        self.coord = User.objects.create_user(
            username="weather_coord",
            password=self.password,
            role=User.Role.COORDINATOR,
        )
        self.volunteer = User.objects.create_user(
            username="weather_vol",
            password=self.password,
            role=User.Role.VOLUNTEER,
        )

    def test_weather_override_requires_coordinator_or_admin(self):
        self.client.login(username="weather_vol", password=self.password)
        resp = self.client.get(reverse("prediction:weather_overrides"))
        self.assertEqual(resp.status_code, 403)

    def test_update_or_create_and_reset_updates_map_data(self):
        self.client.login(username="weather_coord", password=self.password)
        url = reverse("prediction:weather_overrides")

        # 1. Create override for Dhaka
        resp = self.client.post(
            url,
            {
                "station_name": "Dhaka",
                "rainfall": 750.0,
                "relative_humidity": 90.0,
                "cloud_coverage": 7.0,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WeatherOverride.objects.filter(station_name="Dhaka").count(), 1)

        # 2. Posting Dhaka again updates in place (no duplicate rows)
        self.client.post(
            url,
            {
                "station_name": "Dhaka",
                "rainfall": 820.0,
                "relative_humidity": 92.0,
                "cloud_coverage": 7.2,
            },
            follow=True,
        )
        self.assertEqual(WeatherOverride.objects.filter(station_name="Dhaka").count(), 1)
        dhaka_ov = WeatherOverride.objects.get(station_name="Dhaka")
        self.assertEqual(dhaka_ov.rainfall, 820.0)

        # 3. map_data reports Dhaka as 'manual' and High risk
        map_resp = self.client.get(reverse("prediction:map_data"))
        self.assertEqual(map_resp.status_code, 200)
        zones = {z["name"]: z for z in map_resp.json()["flood_risk_zones"]}
        self.assertEqual(zones["Dhaka"]["data_source"], "manual")
        self.assertEqual(zones["Dhaka"]["risk_label"], "High")

        # 4. Reset to seasonal baseline removes row and reverts map_data
        reset_resp = self.client.post(
            reverse("prediction:reset_weather_override", args=[dhaka_ov.id]),
            follow=True,
        )
        self.assertEqual(reset_resp.status_code, 200)
        self.assertFalse(WeatherOverride.objects.filter(station_name="Dhaka").exists())

        map_resp_after = self.client.get(reverse("prediction:map_data"))
        zones_after = {z["name"]: z for z in map_resp_after.json()["flood_risk_zones"]}
        self.assertEqual(zones_after["Dhaka"]["data_source"], "seasonal_average")

    def test_map_data_includes_active_non_fire_and_excludes_resolved_incidents(self):
        self.client.login(username="weather_coord", password=self.password)

        active_flood = Incident.objects.create(
            title="Active Flash Flood",
            incident_type=Incident.IncidentType.FLOOD,
            description="Overflowing river.",
            location="Sylhet",
            latitude=24.9,
            longitude=91.87,
            severity=Incident.Severity.CRITICAL,
            status=Incident.Status.ACTIVE,
        )
        Incident.objects.create(
            title="Resolved Cyclone",
            incident_type=Incident.IncidentType.CYCLONE,
            description="Already cleared.",
            location="Cox's Bazar",
            latitude=21.45,
            longitude=91.97,
            severity=Incident.Severity.HIGH,
            status=Incident.Status.RESOLVED,
        )
        Incident.objects.create(
            title="Resolved Fire",
            incident_type=Incident.IncidentType.FIRE,
            description="Extinguished.",
            location="Dhaka",
            latitude=23.81,
            longitude=90.41,
            severity=Incident.Severity.MEDIUM,
            status=Incident.Status.RESOLVED,
        )

        payload = self.client.get(reverse("prediction:map_data")).json()
        self.assertEqual(len(payload["fire_incidents"]), 0)
        self.assertEqual(len(payload["other_incidents"]), 1)
        other = payload["other_incidents"][0]
        self.assertEqual(other["name"], active_flood.title)
        self.assertEqual(other["incident_type"], "flood")
        self.assertEqual(other["severity"], "critical")
        self.assertEqual(other["url"], f"/incidents/{active_flood.id}/")


class WeatherOverrideWebSocketTests(TransactionTestCase):
    async def test_save_and_delete_broadcast_weather_updates(self):
        communicator = WebsocketCommunicator(application, "/ws/alerts/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        try:
            greeting = await communicator.receive_json_from(timeout=3)
            self.assertEqual(greeting["event_type"], "connected")

            user = await sync_to_async(User.objects.create_user)(
                username="ws_weather_coord",
                password="Password123!",
                role=User.Role.COORDINATOR,
            )
            ov = await sync_to_async(WeatherOverride.objects.create)(
                station_name="Sylhet",
                rainfall=900.0,
                relative_humidity=91.0,
                cloud_coverage=7.1,
                updated_by=user,
            )
            added_msg = await communicator.receive_json_from(timeout=3)
            self.assertEqual(added_msg["event_type"], "weather_update")
            self.assertEqual(added_msg["station_name"], "Sylhet")
            self.assertEqual(added_msg["action"], "added")
            self.assertEqual(added_msg["author"], "ws_weather_coord")

            await sync_to_async(ov.delete)()
            reset_msg = await communicator.receive_json_from(timeout=3)
            self.assertEqual(reset_msg["event_type"], "weather_update")
            self.assertEqual(reset_msg["station_name"], "Sylhet")
            self.assertEqual(reset_msg["action"], "reset")

            # Shelter save triggers silent site_update for live map marker refresh
            await sync_to_async(Shelter.objects.create)(
                name="WS Test Shelter",
                location="Dhaka",
                latitude=23.81,
                longitude=90.41,
            )
            site_msg = await communicator.receive_json_from(timeout=3)
            self.assertEqual(site_msg["event_type"], "site_update")
            self.assertEqual(site_msg["site_type"], "shelter")
            self.assertEqual(site_msg["name"], "WS Test Shelter")
        finally:
            await communicator.disconnect()


class FloodModelTests(TestCase):
    def test_predict_high_and_low_flood_risk(self):
        high = predict_flood_risk(rainfall=600, relative_humidity=85, cloud_coverage=6.5)
        self.assertTrue(high["flood_predicted"])
        self.assertEqual(high["risk_label"], "High")
        self.assertGreaterEqual(high["flood_probability"], 0.5)

        low = predict_flood_risk(rainfall=20, relative_humidity=40, cloud_coverage=3.5)
        self.assertFalse(low["flood_predicted"])
        self.assertEqual(low["risk_label"], "Low")
        self.assertLess(low["flood_probability"], 0.5)

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            predict_flood_risk(rainfall=-1, relative_humidity=50, cloud_coverage=3)
        with self.assertRaises(ValueError):
            predict_flood_risk(rainfall=100, relative_humidity=105, cloud_coverage=3)
        with self.assertRaises(ValueError):
            predict_flood_risk(rainfall=None, relative_humidity=50, cloud_coverage=3)

    def test_out_of_distribution_values_include_warnings(self):
        res = predict_flood_risk(rainfall=2500, relative_humidity=20, cloud_coverage=9.0)
        self.assertIn("warnings", res)
        self.assertEqual(len(res["warnings"]), 3)


class FireSeverityTests(TestCase):
    def test_high_escalation_and_compounding_penalty(self):
        res = calculate_fire_severity(
            material="wood",
            road_access="narrow_alley",
            density="slum",
            time_of_day=2,
            occupancy_type="garment_factory",
        )
        self.assertEqual(res["label"], "High Escalation Risk")
        self.assertFalse(res["floor_applied"])
        self.assertEqual(res["factors"]["compounding_penalty"], 15)
        self.assertEqual(res["score"], 150)

    def test_chemical_occupancy_applies_safety_floor(self):
        res = calculate_fire_severity(
            material="concrete",
            road_access="wide_road",
            density="residential",
            time_of_day=14,
            occupancy_type="chemical",
        )
        self.assertEqual(res["score"], 45)
        self.assertEqual(res["label"], "High Escalation Risk")
        self.assertTrue(res["floor_applied"])

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            calculate_fire_severity("concrete", "wide_road", "residential", time_of_day=24)
        with self.assertRaises(ValueError):
            calculate_fire_severity("concrete", "wide_road", "residential", time_of_day=12, occupancy_type="unknown")


class StationsAndPayloadTests(TestCase):
    def test_nearest_station_and_payload_assembly(self):
        self.assertEqual(len(STATIONS), 33)
        self.assertEqual(find_nearest_station(23.80, 90.40)["name"], "Dhaka")
        self.assertEqual(find_nearest_station(24.89, 91.90)["name"], "Sylhet")

        payload = build_map_payload(
            manual_entries={"Rajshahi": {"rainfall": 600, "relative_humidity": 85, "cloud_coverage": 6.5}},
            month=7,
        )
        zones = {z["name"]: z for z in payload["flood_risk_zones"]}
        self.assertEqual(len(zones), 33)
        self.assertEqual(zones["Rajshahi"]["data_source"], "manual")
        self.assertEqual(zones["Dhaka"]["data_source"], "seasonal_average")

        attached = get_shelter_flood_risk(23.80, 90.40, payload["flood_risk_zones"])
        self.assertEqual(attached["name"], "Dhaka")
