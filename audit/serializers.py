from rest_framework import serializers
from audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default=None)

    class Meta:
        model = AuditEvent
        fields = [
            "id", "workspace", "actor", "actor_username", "action",
            "target_type", "target_id", "description", "metadata", "created_at",
        ]
        read_only_fields = fields
