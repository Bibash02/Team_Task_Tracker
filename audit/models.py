from django.conf import settings
from django.db import models
from common.models import TimeStampedModel

class AuditEvent(TimeStampedModel):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        ASSIGN = "assign", "Assign"
        STATUS_CHANGE = "status_change", "Status Change"
        MEMBER_ADD = "member_add", "Member Added"
        MEMBER_REMOVE = "member_remove", "Member Removed"
        ROLE_CHANGE = "role_change", "Role Changed"

    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_events",
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    target_type = models.CharField(max_length=50)  # e.g. "task", "project", "team"
    target_id = models.CharField(max_length=64)
    description = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"[{self.workspace_id}] {self.action} {self.target_type}:{self.target_id}"
