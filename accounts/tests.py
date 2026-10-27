from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.admin import CustomUserAdmin

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_with_default_role(self):
        user = User.objects.create_user(
            username="volunteer1",
            password="securepassword123",
            email="vol1@example.com",
        )
        self.assertEqual(user.role, User.Role.VOLUNTEER)
        self.assertTrue(user.is_role_volunteer)
        self.assertFalse(user.is_role_admin)
        self.assertFalse(user.is_role_coordinator)
        self.assertFalse(user.is_role_shelter_manager)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_admin_role_does_not_grant_staff_or_superuser(self):
        user = User.objects.create_user(
            username="admin_user",
            password="securepassword123",
            email="admin@example.com",
            role=User.Role.ADMIN,
        )
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_role_admin)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_coordinator_and_shelter_manager(self):
        coord = User.objects.create_user(
            username="coord1",
            password="securepassword123",
            role=User.Role.COORDINATOR,
        )
        shelter_mgr = User.objects.create_user(
            username="mgr1",
            password="securepassword123",
            role=User.Role.SHELTER_MANAGER,
        )
        self.assertTrue(coord.is_role_coordinator)
        self.assertTrue(shelter_mgr.is_role_shelter_manager)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="superadmin",
            password="superpassword123",
            email="super@example.com",
            role=User.Role.ADMIN,
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.Role.ADMIN)

    def test_user_str_representation(self):
        user = User.objects.create_user(
            username="testuser",
            password="password123",
            role=User.Role.COORDINATOR,
        )
        self.assertEqual(str(user), "testuser (Warehouse Coordinator)")

    def test_admin_registration(self):
        self.assertIn(User, site._registry)
        admin_instance = site._registry[User]
        self.assertIsInstance(admin_instance, CustomUserAdmin)
        self.assertIn("role", admin_instance.list_display)
        self.assertIn("role", admin_instance.list_filter)


class AuthenticationAndDashboardRoutingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ValidPass123!"
        self.admin_user = User.objects.create_user(
            username="admin_test",
            password=self.password,
            email="admin@test.com",
            role=User.Role.ADMIN,
        )
        self.coord_user = User.objects.create_user(
            username="coord_test",
            password=self.password,
            email="coord@test.com",
            role=User.Role.COORDINATOR,
        )
        self.shelter_user = User.objects.create_user(
            username="shelter_test",
            password=self.password,
            email="shelter@test.com",
            role=User.Role.SHELTER_MANAGER,
        )
        self.volunteer_user = User.objects.create_user(
            username="volunteer_test",
            password=self.password,
            email="vol@test.com",
            role=User.Role.VOLUNTEER,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        routes = [
            reverse("dashboard_admin"),
            reverse("dashboard_coordinator"),
            reverse("dashboard_shelter_manager"),
            reverse("dashboard_volunteer"),
            reverse("dashboard_redirect"),
            reverse("admin_create_account"),
        ]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response.url)

    def test_login_successful_and_redirects_by_role(self):
        cases = [
            (self.admin_user, reverse("dashboard_admin")),
            (self.coord_user, reverse("dashboard_coordinator")),
            (self.shelter_user, reverse("dashboard_shelter_manager")),
            (self.volunteer_user, reverse("dashboard_volunteer")),
        ]
        for user, expected_target in cases:
            response = self.client.post(
                reverse("login"),
                {"username": user.username, "password": self.password},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.redirect_chain[-1][0], expected_target)
            self.client.logout()

    def test_failed_login_displays_error(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin_test", "password": "WrongPassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_logout_redirects_to_login(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.post(reverse("logout"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], reverse("login"))

    def test_cross_role_access_forbidden(self):
        # Volunteer cannot access admin, coordinator, or shelter-manager dashboards
        self.client.login(username=self.volunteer_user.username, password=self.password)
        res_admin = self.client.get(reverse("dashboard_admin"))
        self.assertEqual(res_admin.status_code, 403)
        res_coord = self.client.get(reverse("dashboard_coordinator"))
        self.assertEqual(res_coord.status_code, 403)
        res_shelter = self.client.get(reverse("dashboard_shelter_manager"))
        self.assertEqual(res_shelter.status_code, 403)
        # Volunteer CAN access volunteer dashboard
        res_vol = self.client.get(reverse("dashboard_volunteer"))
        self.assertEqual(res_vol.status_code, 200)
        self.client.logout()

        # Shelter Manager cannot access admin or coordinator dashboards
        self.client.login(username=self.shelter_user.username, password=self.password)
        res_admin = self.client.get(reverse("dashboard_admin"))
        self.assertEqual(res_admin.status_code, 403)
        res_coord = self.client.get(reverse("dashboard_coordinator"))
        self.assertEqual(res_coord.status_code, 403)
        # Shelter Manager CAN access shelter manager dashboard
        res_shelter = self.client.get(reverse("dashboard_shelter_manager"))
        self.assertEqual(res_shelter.status_code, 200)
        self.client.logout()


class AdminAccountCreationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin_sys",
            password="SysPassword123!",
            email="sys@crisisnet.org",
            role=User.Role.ADMIN,
        )
        self.volunteer_user = User.objects.create_user(
            username="volunteer_sys",
            password="VolPassword123!",
            role=User.Role.VOLUNTEER,
        )

    def test_non_admin_cannot_access_create_account(self):
        self.client.login(username="volunteer_sys", password="VolPassword123!")
        response = self.client.get(reverse("admin_create_account"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_create_account(self):
        self.client.login(username="admin_sys", password="SysPassword123!")
        response = self.client.get(reverse("admin_create_account"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Operator Account")

    def test_admin_creates_shelter_manager_successfully(self):
        self.client.login(username="admin_sys", password="SysPassword123!")
        payload = {
            "username": "new_manager",
            "email": "manager@crisisnet.org",
            "first_name": "Rahim",
            "last_name": "Uddin",
            "role": User.Role.SHELTER_MANAGER,
            "password": "ManagerSecurePass123!",
            "confirm_password": "ManagerSecurePass123!",
        }
        response = self.client.post(reverse("admin_create_account"), payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="new_manager").exists())
        created = User.objects.get(username="new_manager")
        self.assertEqual(created.role, User.Role.SHELTER_MANAGER)
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)

    def test_form_rejects_admin_role_escalation(self):
        self.client.login(username="admin_sys", password="SysPassword123!")
        payload = {
            "username": "hacker_admin",
            "email": "hacker@crisisnet.org",
            "role": "admin",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        response = self.client.post(reverse("admin_create_account"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="hacker_admin").exists())
        self.assertContains(response, "Select a valid choice")

    def test_form_rejects_mismatched_passwords(self):
        self.client.login(username="admin_sys", password="SysPassword123!")
        payload = {
            "username": "coord_mismatch",
            "email": "coord_mis@crisisnet.org",
            "role": User.Role.COORDINATOR,
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
        }
        response = self.client.post(reverse("admin_create_account"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="coord_mismatch").exists())
        self.assertContains(response, "Passwords do not match")
