from django.contrib import admin
from audit.models import AuditEvent

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "workspace", "actor", "action", "target_type", "target_id")
    list_filter = ("action", "target_type", "workspace")
    search_fields = ("description", "target_id")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
