from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        COORDINATOR = "coordinator", "Warehouse Coordinator"
        SHELTER_MANAGER = "shelter_manager", "Shelter Manager"
        VOLUNTEER = "volunteer", "Volunteer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VOLUNTEER,
        help_text="Role determining user dashboard access and permissions",
    )

    @property
    def is_role_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_role_coordinator(self):
        return self.role == self.Role.COORDINATOR

    @property
    def is_role_shelter_manager(self):
        return self.role == self.Role.SHELTER_MANAGER

    @property
    def is_role_volunteer(self):
        return self.role == self.Role.VOLUNTEER

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
