from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from django.test import TestCase
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
        # Admin role in domain must NOT automatically grant Django staff/superuser
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
