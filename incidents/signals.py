from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Incident, OperationalNotice
from .broadcasts import broadcast_incident_alert, broadcast_notice_alert


@receiver(post_save, sender=Incident)
def on_incident_save(sender, instance, created, **kwargs):
    action = "reported" if created else "updated"
    broadcast_incident_alert(instance, action=action)


@receiver(post_save, sender=OperationalNotice)
def on_notice_save(sender, instance, created, **kwargs):
    if created:
        broadcast_notice_alert(instance)
