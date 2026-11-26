from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from incidents.admin import IncidentAdmin
from incidents.models import Incident
from requests_app.models import Request
from shelters.models import Shelter

User = get_user_model()


class IncidentModelTests(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            username="reporter1",
            password="Password123!",
            role=User.Role.COORDINATOR,
        )
        self.shelter1 = Shelter.objects.create(
            name="Chilmari College Shelter",
            location="Kurigram",
            latitude=25.5641,
            longitude=89.6742,
            capacity=300,
            current_occupancy=120,
        )

    def test_create_incident_successfully(self):
        incident = Incident.objects.create(
            title="Brahmaputra Flash Flood 2026",
            incident_type=Incident.IncidentType.FLOOD,
            description="Water levels exceeded danger mark causing embankment breach.",
            location="Chilmari, Kurigram",
            latitude=25.5641,
            longitude=89.6742,
            severity=Incident.Severity.CRITICAL,
            status=Incident.Status.ACTIVE,
            reported_by=self.reporter,
        )
        incident.affected_shelters.add(self.shelter1)

        self.assertEqual(incident.title, "Brahmaputra Flash Flood 2026")
        self.assertEqual(incident.severity, Incident.Severity.CRITICAL)
        self.assertEqual(incident.status, Incident.Status.ACTIVE)
        self.assertTrue(incident.is_active)
        self.assertIn(self.shelter1, incident.affected_shelters.all())
        self.assertEqual(incident.reported_by, self.reporter)

    def test_admin_registration(self):
        self.assertIn(Incident, site._registry)
        admin_instance = site._registry[Incident]
        self.assertIsInstance(admin_instance, IncidentAdmin)
        self.assertIn("severity", admin_instance.list_display)
        self.assertIn("affected_shelters", admin_instance.filter_horizontal)


class IncidentViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ValidPass123!"

        self.admin_user = User.objects.create_user(
            username="admin_user",
            password=self.password,
            role=User.Role.ADMIN,
        )
        self.coord_user = User.objects.create_user(
            username="coord_user",
            password=self.password,
            role=User.Role.COORDINATOR,
        )
        self.volunteer = User.objects.create_user(
            username="volunteer_user",
            password=self.password,
            role=User.Role.VOLUNTEER,
        )

        self.shelter = Shelter.objects.create(
            name="Roumari Model School",
            location="Roumari, Kurigram",
            capacity=200,
            current_occupancy=80,
        )

        self.incident = Incident.objects.create(
            title="Roumari Flash Flood",
            incident_type=Incident.IncidentType.FLOOD,
            description="Severe flooding affecting multiple low-lying chars.",
            location="Roumari",
            latitude=25.5600,
            longitude=89.8500,
            severity=Incident.Severity.HIGH,
            status=Incident.Status.ACTIVE,
            reported_by=self.coord_user,
        )
        self.incident.affected_shelters.add(self.shelter)

        # Create connected request using existing Request model
        self.req1 = Request.objects.create(
            shelter_name=self.shelter.name,
            item_name="Dry Rations & Water",
            quantity=150,
            status=Request.Status.PENDING,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        res_list = self.client.get(reverse("incident_list"))
        self.assertEqual(res_list.status_code, 302)
        self.assertIn(reverse("login"), res_list.url)

        res_detail = self.client.get(reverse("incident_detail", args=[self.incident.id]))
        self.assertEqual(res_detail.status_code, 302)
        self.assertIn(reverse("login"), res_detail.url)

    def test_incident_list_view_and_filtering(self):
        self.client.login(username="volunteer_user", password=self.password)
        response = self.client.get(reverse("incident_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Roumari Flash Flood")

        # Test filter matching
        res_filtered = self.client.get(f"{reverse('incident_list')}?severity=high")
        self.assertEqual(res_filtered.status_code, 200)
        self.assertContains(res_filtered, "Roumari Flash Flood")

        # Test filter mismatch
        res_empty = self.client.get(f"{reverse('incident_list')}?severity=low")
        self.assertEqual(res_empty.status_code, 200)
        self.assertNotContains(res_empty, "Roumari Flash Flood")

    def test_incident_detail_displays_affected_shelters_and_connected_requests(self):
        self.client.login(username="volunteer_user", password=self.password)
        response = self.client.get(reverse("incident_detail", args=[self.incident.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Roumari Flash Flood")
        self.assertContains(response, "Roumari Model School")
        self.assertContains(response, "Dry Rations")
        self.assertContains(response, "150")

    def test_authorized_users_can_update_incident_status(self):
        # Admin update
        self.client.login(username="admin_user", password=self.password)
        url = reverse("update_incident_status", args=[self.incident.id])
        response = self.client.post(
            url,
            {"status": Incident.Status.CONTAINED, "severity": Incident.Severity.MEDIUM},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.Status.CONTAINED)
        self.assertEqual(self.incident.severity, Incident.Severity.MEDIUM)

    def test_unauthorized_user_cannot_update_incident_status(self):
        # Random volunteer who did not report it
        self.client.login(username="volunteer_user", password=self.password)
        url = reverse("update_incident_status", args=[self.incident.id])
        response = self.client.post(
            url,
            {"status": Incident.Status.RESOLVED},
        )
        self.assertEqual(response.status_code, 403)

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.Status.ACTIVE)

    def test_create_operational_notice_authorized(self):
        self.client.login(username="coord_user", password=self.password)
        url = reverse("create_operational_notice")
        response = self.client.post(
            url,
            {
                "title": "Severe Cyclone Warning",
                "message": "Immediate evacuation advisory for coastal shelters.",
                "priority": "urgent",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        from incidents.models import OperationalNotice
        self.assertTrue(OperationalNotice.objects.filter(title="Severe Cyclone Warning").exists())

    def test_create_operational_notice_unauthorized(self):
        self.client.login(username="volunteer_user", password=self.password)
        url = reverse("create_operational_notice")
        response = self.client.post(
            url,
            {
                "title": "Unauthorized Bulletin",
                "message": "Testing unauthorized block.",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_map_and_coordinator_pages_include_alerts_widget(self):
        self.client.login(username="coord_user", password=self.password)
        for url in [reverse("prediction:map"), reverse("dashboard")]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "live-alert-toast-container")
            self.assertContains(response, "/ws/alerts/")

    def test_fire_assessment_and_map_data_integration(self):
        # Non-fire incident returns None
        self.assertIsNone(self.incident.get_fire_assessment())

        # Chemical fire with favorable conditions still hits High floor
        chem_fire = Incident.objects.create(
            title="Chemical Warehouse Blaze",
            incident_type=Incident.IncidentType.FIRE,
            description="Chemical drums ignited.",
            location="Sitakunda",
            latitude=22.62,
            longitude=91.66,
            severity=Incident.Severity.CRITICAL,
            status=Incident.Status.ACTIVE,
            occupancy_type=Incident.OccupancyType.CHEMICAL,
            building_material=Incident.BuildingMaterial.CONCRETE,
            road_access=Incident.RoadAccess.WIDE_ROAD,
            area_density=Incident.AreaDensity.RESIDENTIAL,
            incident_hour=14,
        )
        assessment = chem_fire.get_fire_assessment()
        self.assertEqual(assessment["score"], 45)
        self.assertEqual(assessment["label"], "High Escalation Risk")
        self.assertTrue(assessment["floor_applied"])

        self.client.login(username="coord_user", password=self.password)
        resp = self.client.get(reverse("prediction:map_data"))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(len(payload["fire_incidents"]), 1)
        fire_entry = payload["fire_incidents"][0]
        self.assertEqual(fire_entry["occupancy_type"], "chemical")
        self.assertEqual(fire_entry["score"], 45)
        self.assertEqual(fire_entry["label"], "High Escalation Risk")
        self.assertTrue(fire_entry["floor_applied"])
        self.assertIn("road_access", fire_entry["factors"])


class AlertBroadcastWebSocketTests(TransactionTestCase):
    async def test_alert_consumer_receives_incident_and_notice_broadcasts(self):
        from asgiref.sync import sync_to_async
        from channels.testing import WebsocketCommunicator
        from crisisnet.asgi import application
        from incidents.models import OperationalNotice

        communicator = WebsocketCommunicator(application, "/ws/alerts/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        try:
            greeting = await communicator.receive_json_from(timeout=3)
            self.assertEqual(greeting["event_type"], "connected")

            # Creating an incident should trigger post_save -> broadcast_incident_alert
            incident = await sync_to_async(Incident.objects.create)(
                title="Padma Embankment Breach",
                incident_type=Incident.IncidentType.FLOOD,
                description="Riverbank overflow near Munshiganj.",
                location="Munshiganj",
                latitude=23.5422,
                longitude=90.5305,
                severity=Incident.Severity.HIGH,
                status=Incident.Status.ACTIVE,
            )
            inc_msg = await communicator.receive_json_from(timeout=3)
            self.assertEqual(inc_msg["event_type"], "incident_update")
            self.assertEqual(inc_msg["id"], incident.id)
            self.assertEqual(inc_msg["title"], "Padma Embankment Breach")
            self.assertEqual(inc_msg["action"], "reported")

            # Creating an operational notice should trigger post_save -> broadcast_operational_notice
            user = await sync_to_async(User.objects.create_user)(
                username="ws_coord",
                password="Password123!",
                role=User.Role.COORDINATOR,
            )
            notice = await sync_to_async(OperationalNotice.objects.create)(
                title="Evacuation Route Open",
                message="Use Highway N8 for Munshiganj relief convoy.",
                priority=OperationalNotice.Priority.URGENT,
                created_by=user,
            )
            notice_msg = await communicator.receive_json_from(timeout=3)
            self.assertEqual(notice_msg["event_type"], "operational_notice")
            self.assertEqual(notice_msg["id"], notice.id)
            self.assertEqual(notice_msg["title"], "Evacuation Route Open")
            self.assertEqual(notice_msg["priority"], "urgent")
            self.assertEqual(notice_msg["author"], "ws_coord")
        finally:
            await communicator.disconnect()

