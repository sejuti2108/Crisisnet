import json
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_payload(event_type: str, data: dict):
    """
    Publish an event to the 'alerts' Channel Layer group.
    Any active web client connected to /ws/alerts/ will receive this immediately.
    """
    try:
        layer = get_channel_layer()
        if not layer:
            return
        async_to_sync(layer.group_send)(
            "alerts",
            {
                "type": "alert_broadcast",
                "data": {
                    "event_type": event_type,
                    **data,
                },
            },
        )
    except Exception as e:
        logger.warning("Failed to broadcast alert over Channel Layer: %s", e)


def broadcast_incident_alert(incident, action: str = "updated"):
    """
    Broadcast incident creation, severity escalation, or status update.
    """
    broadcast_payload(
        event_type="incident_update",
        data={
            "id": incident.id,
            "title": incident.title,
            "incident_type": incident.incident_type,
            "incident_type_display": incident.get_incident_type_display(),
            "severity": incident.severity,
            "severity_display": incident.get_severity_display(),
            "status": incident.status,
            "status_display": incident.get_status_display(),
            "location": incident.location,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "action": action,
            "url": f"/incidents/{incident.id}/",
            "timestamp": incident.updated_at.strftime("%H:%M:%S") if incident.updated_at else "",
        },
    )


def broadcast_operational_notice(notice):
    """
    Broadcast a high-priority operational notice / bulletin to all active clients.
    """
    broadcast_payload(
        event_type="operational_notice",
        data={
            "id": notice.id,
            "title": notice.title,
            "message": notice.message,
            "priority": notice.priority,
            "priority_display": notice.get_priority_display(),
            "target_role": notice.target_role,
            "author": notice.created_by.username if notice.created_by else "HQ Command",
            "timestamp": notice.created_at.strftime("%H:%M:%S") if notice.created_at else "",
        },
    )


# Alias
broadcast_notice_alert = broadcast_operational_notice

