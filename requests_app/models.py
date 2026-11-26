from django.db import models
from warehouses.models import Warehouse


class Request(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DISPATCHED = "dispatched", "Dispatched"

    shelter = models.ForeignKey(
        "shelters.Shelter",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requests",
    )
    shelter_name = models.CharField(max_length=200, blank=True)
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    fulfilled_by = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Keep the shelter link and the shelter name in sync.
        if self.shelter_id is None and self.shelter_name:
            from shelters.models import Shelter
            self.shelter = Shelter.objects.filter(name=self.shelter_name).first()
        if self.shelter_id is not None:
            self.shelter_name = self.shelter.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} x{self.quantity} for {self.shelter_name} ({self.status})"


class AuditLog(models.Model):
    request = models.ForeignKey(Request, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    actor = models.CharField(max_length=100, default="coordinator")
    details = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.actor}: {self.action} (request {self.request_id})"