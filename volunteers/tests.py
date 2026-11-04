from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from incidents.models import Incident
from shelters.models import Shelter
from volunteers.admin import VolunteerAdmin
from volunteers.models import Volunteer

User = get_user_model()


class VolunteerModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_vol",
            password="Password123!",
            role=User.Role.VOLUNTEER,
        )
        self.incident = Incident.objects.create(
            title="Flood Zone 1",
            location="Sunamganj",
            description="Embankment broken",
        )
        self.shelter = Shelter.objects.create(
            name="Primary School Shelter",
            location="Sunamganj Sadar",
            capacity=150,
        )

    def test_create_volunteer_successfully(self):
        vol = Volunteer.objects.create(
            user=self.user,
            phone="+8801711112222",
            skills="First Aid & Evacuation",
            availability=Volunteer.Availability.AVAILABLE,
        )
        self.assertEqual(vol.user, self.user)
        self.assertEqual(vol.availability, Volunteer.Availability.AVAILABLE)
        self.assertTrue(vol.is_available)
        self.assertFalse(vol.is_deployed)
        self.assertIn("test_vol", str(vol))

    def test_auto_deployment_status_on_assignment(self):
        vol = Volunteer.objects.create(
            user=self.user,
            phone="+8801711112222",
            assigned_incident=self.incident,
        )
        self.assertEqual(vol.availability, Volunteer.Availability.DEPLOYED)
        self.assertTrue(vol.is_deployed)

    def test_unavailable_volunteer_cannot_have_active_assignments(self):
        vol = Volunteer(
            user=self.user,
            availability=Volunteer.Availability.UNAVAILABLE,
            assigned_incident=self.incident,
        )
        with self.assertRaises(ValidationError):
            vol.clean()

    def test_admin_registration(self):
        self.assertIn(Volunteer, site._registry)
        admin_instance = site._registry[Volunteer]
        self.assertIsInstance(admin_instance, VolunteerAdmin)
        self.assertIn("availability", admin_instance.list_filter)
        self.assertIn("skills", admin_instance.search_fields)


class VolunteerManagementViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ValidPass123!"

        self.admin_user = User.objects.create_user(
            username="admin_mgr",
            password=self.password,
            role=User.Role.ADMIN,
        )
        self.coord_user = User.objects.create_user(
            username="coord_mgr",
            password=self.password,
            role=User.Role.COORDINATOR,
        )
        self.shelter_mgr = User.objects.create_user(
            username="shelter_mgr",
            password=self.password,
            role=User.Role.SHELTER_MANAGER,
        )
        self.vol_user = User.objects.create_user(
            username="field_volunteer",
            password=self.password,
            role=User.Role.VOLUNTEER,
        )
        self.volunteer = Volunteer.objects.create(
            user=self.vol_user,
            phone="+8801799998888",
            skills="Search and Rescue",
            availability=Volunteer.Availability.AVAILABLE,
        )

        self.incident = Incident.objects.create(
            title="Fire at Warehouse Area",
            location="Sitakunda",
            description="Chemical fire requiring containment",
            severity=Incident.Severity.CRITICAL,
        )
        self.shelter = Shelter.objects.create(
            name="Sitakunda Relief Camp",
            location="Sitakunda",
            capacity=200,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse("volunteer_management"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_unauthorized_roles_forbidden(self):
        # Volunteer cannot access management
        self.client.login(username="field_volunteer", password=self.password)
        res_vol = self.client.get(reverse("volunteer_management"))
        self.assertEqual(res_vol.status_code, 403)
        self.client.logout()

        # Shelter Manager cannot access management
        self.client.login(username="shelter_mgr", password=self.password)
        res_sm = self.client.get(reverse("volunteer_management"))
        self.assertEqual(res_sm.status_code, 403)
        self.client.logout()

    def test_admin_and_coordinator_can_access_management(self):
        # Admin access
        self.client.login(username="admin_mgr", password=self.password)
        res_admin = self.client.get(reverse("volunteer_management"))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, "field_volunteer")
        self.client.logout()

        # Coordinator access
        self.client.login(username="coord_mgr", password=self.password)
        res_coord = self.client.get(reverse("volunteer_management"))
        self.assertEqual(res_coord.status_code, 200)
        self.assertContains(res_coord, "field_volunteer")
        self.client.logout()

    def test_coordinator_assigns_volunteer_successfully(self):
        self.client.login(username="coord_mgr", password=self.password)
        url = reverse("assign_volunteer", args=[self.volunteer.id])
        payload = {
            "assigned_incident": self.incident.id,
            "assigned_shelter": self.shelter.id,
            "availability": Volunteer.Availability.DEPLOYED,
        }
        response = self.client.post(url, payload, follow=True)
        self.assertEqual(response.status_code, 200)

        self.volunteer.refresh_from_db()
        self.assertEqual(self.volunteer.assigned_incident, self.incident)
        self.assertEqual(self.volunteer.assigned_shelter, self.shelter)
        self.assertEqual(self.volunteer.availability, Volunteer.Availability.DEPLOYED)

    def test_assignment_conflict_rejected_when_unavailable(self):
        self.client.login(username="coord_mgr", password=self.password)
        url = reverse("assign_volunteer", args=[self.volunteer.id])
        payload = {
            "assigned_incident": self.incident.id,
            "availability": Volunteer.Availability.UNAVAILABLE,
        }
        response = self.client.post(url, payload, follow=True)
        self.assertEqual(response.status_code, 200)

        self.volunteer.refresh_from_db()
        # Incident should not be assigned
        self.assertIsNone(self.volunteer.assigned_incident)

    def test_unauthorized_user_cannot_assign_volunteer(self):
        self.client.login(username="shelter_mgr", password=self.password)
        url = reverse("assign_volunteer", args=[self.volunteer.id])
        response = self.client.post(url, {"assigned_incident": self.incident.id})
        self.assertEqual(response.status_code, 403)


class VolunteerDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ValidPass123!"

        self.vol_user = User.objects.create_user(
            username="active_vol",
            password=self.password,
            role=User.Role.VOLUNTEER,
        )
        self.incident = Incident.objects.create(
            title="Chakaria Flash Flood",
            location="Cox's Bazar",
            description="Water level high in Matamuhuri river",
        )
        self.volunteer = Volunteer.objects.create(
            user=self.vol_user,
            phone="+8801811223344",
            skills="First Aid Support",
            assigned_incident=self.incident,
            availability=Volunteer.Availability.DEPLOYED,
        )

    def test_volunteer_views_dashboard_and_assigned_incident(self):
        self.client.login(username="active_vol", password=self.password)
        response = self.client.get(reverse("dashboard_volunteer"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chakaria Flash Flood")
        self.assertContains(response, "First Aid Support")

    def test_volunteer_updates_contact_and_skills(self):
        self.client.login(username="active_vol", password=self.password)
        payload = {
            "phone": "+8801899001122",
            "skills": "Medical and Logistics",
            "availability": Volunteer.Availability.DEPLOYED,
        }
        response = self.client.post(reverse("dashboard_volunteer"), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        self.volunteer.refresh_from_db()
        self.assertEqual(self.volunteer.phone, "+8801899001122")
        self.assertEqual(self.volunteer.skills, "Medical and Logistics")
