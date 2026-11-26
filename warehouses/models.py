from django.conf import settings
from django.db import models


class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="warehouses",
        limit_choices_to={"role": "coordinator"},
    )

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=20, default="units")

    def __str__(self):
        return f"{self.item_name} ({self.quantity} {self.unit}) at {self.warehouse.name}"