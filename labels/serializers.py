from rest_framework import serializers
from labels.models import Label


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ["id", "workspace", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_workspace(self, workspace):
        request = self.context["request"]
        if not request.user.is_superuser and not workspace.memberships.filter(user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this workspace.")
        return workspace
