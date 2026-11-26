from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from incidents.broadcasts import broadcast_payload
from shelters.models import Shelter
from warehouses.models import Warehouse
from .models import WeatherOverride


def _broadcast_weather_change(instance: WeatherOverride, action: str):
    broadcast_payload(
        event_type="weather_update",
        data={
            "station_name": instance.station_name,
            "action": action,
            "author": instance.updated_by.username if instance.updated_by else "HQ Command",
            "timestamp": timezone.localtime(timezone.now()).strftime("%H:%M:%S"),
        },
    )


def _broadcast_site_change(site_type: str, instance, action: str):
    broadcast_payload(
        event_type="site_update",
        data={
            "site_type": site_type,
            "name": instance.name,
            "action": action,
        },
    )


@receiver(post_save, sender=WeatherOverride)
def on_weather_override_save(sender, instance, created, **kwargs):
    action = "added" if created else "updated"
    _broadcast_weather_change(instance, action=action)


@receiver(post_delete, sender=WeatherOverride)
def on_weather_override_delete(sender, instance, **kwargs):
    _broadcast_weather_change(instance, action="reset")


@receiver(post_save, sender=Shelter)
def on_shelter_save(sender, instance, created, **kwargs):
    _broadcast_site_change("shelter", instance, "created" if created else "updated")


@receiver(post_delete, sender=Shelter)
def on_shelter_delete(sender, instance, **kwargs):
    _broadcast_site_change("shelter", instance, "deleted")


@receiver(post_save, sender=Warehouse)
def on_warehouse_save(sender, instance, created, **kwargs):
    _broadcast_site_change("warehouse", instance, "created" if created else "updated")


@receiver(post_delete, sender=Warehouse)
def on_warehouse_delete(sender, instance, **kwargs):
    _broadcast_site_change("warehouse", instance, "deleted")
