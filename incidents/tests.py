from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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
