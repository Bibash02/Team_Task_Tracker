from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from common.mixins import WorkspaceScopedQuerysetMixin
from common.permissions import IsWorkspaceMember
from audit.models import AuditEvent
from audit.serializers import AuditEventSerializer


class AuditEventViewSet(WorkspaceScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only: audit trail is never editable via the API.
    Filter examples:
      /api/audit-events/?workspace=<id>
      /api/audit-events/?target_type=task&target_id=<uuid>
      /api/audit-events/?action=status_change
    """
    serializer_class = AuditEventSerializer
    permission_classes = [IsWorkspaceMember]
    workspace_lookup = "workspace"
    select_related_fields = ("workspace", "actor")
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["workspace", "action", "target_type", "target_id", "actor"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_base_queryset(self):
        return AuditEvent.objects.all()
