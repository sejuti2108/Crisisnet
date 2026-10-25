from django.contrib import admin
from .models import Request, AuditLog

admin.site.register(Request)
admin.site.register(AuditLog)