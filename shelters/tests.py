from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from requests_app.models import Request
from shelters.admin import ShelterAdmin
from shelters.models import Shelter
from warehouses.models import InventoryItem, Warehouse

User = get_user_model()


class ShelterModelTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="shelter_mgr",
            password="ManagerPass123!",
            role=User.Role.SHELTER_MANAGER,
        )

    def test_create_shelter_successfully(self):
        shelter = Shelter.objects.create(
            name="Kurigram High School Shelter",
            location="Kurigram Sadar",
            latitude=25.8073,
            longitude=89.6295,
            capacity=250,
            current_occupancy=50,
            manager=self.manager,
        )
        self.assertEqual(shelter.capacity, 250)
        self.assertEqual(shelter.current_occupancy, 50)
        self.assertEqual(shelter.available_capacity, 200)
        self.assertEqual(shelter.occupancy_percentage, 20.0)
        self.assertEqual(shelter.status, Shelter.Status.OPEN)
        self.assertEqual(shelter.manager, self.manager)

    def test_occupancy_exceeding_capacity_raises_validation_error(self):
        shelter = Shelter(
            name="Overcrowded Shelter",
            location="Sunamganj",
            capacity=100,
            current_occupancy=150,
            manager=self.manager,
        )
        with self.assertRaises(ValidationError):
            shelter.clean()

    def test_shelter_auto_status_full_when_occupancy_reaches_capacity(self):
        shelter = Shelter.objects.create(
            name="Full Shelter",
            location="Sylhet",
            capacity=100,
            current_occupancy=100,
            manager=self.manager,
        )
        self.assertEqual(shelter.status, Shelter.Status.FULL)
        self.assertEqual(shelter.available_capacity, 0)
        self.assertEqual(shelter.occupancy_percentage, 100.0)

    def test_admin_registration(self):
        self.assertIn(Shelter, site._registry)
        admin_instance = site._registry[Shelter]
        self.assertIsInstance(admin_instance, ShelterAdmin)
        self.assertIn("capacity", admin_instance.list_display)
        self.assertIn("status", admin_instance.list_filter)


class ShelterManagerDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ValidPass123!"

        self.mgr_a = User.objects.create_user(
            username="manager_a",
            password=self.password,
            role=User.Role.SHELTER_MANAGER,
        )
        self.mgr_b = User.objects.create_user(
            username="manager_b",
            password=self.password,
            role=User.Role.SHELTER_MANAGER,
        )
        self.volunteer = User.objects.create_user(
            username="vol_user",
            password=self.password,
            role=User.Role.VOLUNTEER,
        )

        self.shelter_a = Shelter.objects.create(
            name="Shelter Alpha",
            location="Dhanmondi, Dhaka",
            latitude=23.7461,
            longitude=90.3742,
            capacity=100,
            current_occupancy=30,
            manager=self.mgr_a,
        )
        self.shelter_b = Shelter.objects.create(
            name="Shelter Beta",
            location="Uttara, Dhaka",
            latitude=23.8759,
            longitude=90.3795,
            capacity=150,
            current_occupancy=40,
            manager=self.mgr_b,
        )

        # Create warehouse and inventory for regional stock check
        self.warehouse = Warehouse.objects.create(
            name="Central Relief Depot",
            latitude=23.8103,
            longitude=90.4125,
        )
        self.stock_item = InventoryItem.objects.create(
            warehouse=self.warehouse,
            item_name="Blankets",
            quantity=500,
            unit="pieces",
        )

    def test_unauthenticated_access_redirects(self):
        response = self.client.get(reverse("dashboard_shelter_manager"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_non_shelter_manager_access_forbidden(self):
        self.client.login(username="vol_user", password=self.password)
        response = self.client.get(reverse("dashboard_shelter_manager"))
        self.assertEqual(response.status_code, 403)

    def test_manager_views_assigned_shelter_and_stock(self):
        self.client.login(username="manager_a", password=self.password)
        response = self.client.get(reverse("dashboard_shelter_manager"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shelter Alpha")
        self.assertContains(response, "Central Relief Depot")
        self.assertContains(response, "Blankets")

    def test_manager_cannot_view_unauthorized_shelter(self):
        self.client.login(username="manager_a", password=self.password)
        # Manager A attempts to view Shelter B
        response = self.client.get(
            f"{reverse('dashboard_shelter_manager')}?shelter_id={self.shelter_b.id}"
        )
        self.assertEqual(response.status_code, 403)

    def test_update_occupancy_successfully(self):
        self.client.login(username="manager_a", password=self.password)
        url = reverse("update_shelter_occupancy", args=[self.shelter_a.id])
        response = self.client.post(url, {"current_occupancy": 85}, follow=True)
        self.assertEqual(response.status_code, 200)

        self.shelter_a.refresh_from_db()
        self.assertEqual(self.shelter_a.current_occupancy, 85)

    def test_update_occupancy_exceeding_capacity_rejected(self):
        self.client.login(username="manager_a", password=self.password)
        url = reverse("update_shelter_occupancy", args=[self.shelter_a.id])
        response = self.client.post(url, {"current_occupancy": 500}, follow=True)
        self.assertEqual(response.status_code, 200)

        self.shelter_a.refresh_from_db()
        self.assertEqual(self.shelter_a.current_occupancy, 30)  # unchanged

    def test_manager_cannot_update_other_shelter(self):
        self.client.login(username="manager_a", password=self.password)
        url = reverse("update_shelter_occupancy", args=[self.shelter_b.id])
        response = self.client.post(url, {"current_occupancy": 10})
        self.assertEqual(response.status_code, 403)

    def test_submit_supply_request_successfully(self):
        self.client.login(username="manager_a", password=self.password)
        url = reverse("create_supply_request", args=[self.shelter_a.id])
        response = self.client.post(
            url,
            {"item_name": "Emergency Medical Kits", "quantity": 25},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # Verify Request created in DB
        self.assertTrue(
            Request.objects.filter(
                shelter_name="Shelter Alpha",
                item_name="Emergency Medical Kits",
                quantity=25,
            ).exists()
        )
        req = Request.objects.get(shelter_name="Shelter Alpha")
        self.assertEqual(req.status, Request.Status.PENDING)

    def test_unauthorized_user_cannot_submit_supply_request(self):
        self.client.login(username="manager_a", password=self.password)
        url = reverse("create_supply_request", args=[self.shelter_b.id])
        response = self.client.post(
            url,
            {"item_name": "Rice (kg)", "quantity": 100},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Request.objects.filter(item_name="Rice (kg)").exists())
