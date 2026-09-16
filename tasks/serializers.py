from rest_framework import serializers
from tasks.models import Task, AssignmentRule
from labels.serializers import LabelSerializer
from labels.models import Label


class TaskListSerializer(serializers.ModelSerializer):
    """Lean list serializer — avoids nested comment counts etc. to stay N+1-safe."""
    assignee_username = serializers.CharField(source="assignee.username", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True)
    label_names = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "project", "project_name", "title", "status", "priority",
            "assignee", "assignee_username", "label_names", "due_date", "created_at",
        ]

    def get_label_names(self, obj):
        # Relies on the viewset prefetching `labels` — no extra query per row.
        return [label.name for label in obj.labels.all()]


class TaskDetailSerializer(serializers.ModelSerializer):
    labels_detail = LabelSerializer(source="labels", many=True, read_only=True)
    label_ids = serializers.PrimaryKeyRelatedField(
        source="labels", many=True, queryset=Label.objects.all(), write_only=True, required=False
    )
    comment_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            "id", "project", "title", "description", "status", "priority",
            "assignee", "created_by", "labels_detail", "label_ids",
            "comment_count", "due_date", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "comment_count", "created_at", "updated_at"]

    def validate(self, attrs):
        project = attrs.get("project") or getattr(self.instance, "project", None)
        assignee = attrs.get("assignee")
        if project and assignee:
            if not project.team.memberships.filter(user=assignee).exists():
                raise serializers.ValidationError(
                    {"assignee": "Assignee must be a member of the task's team."}
                )
        return attrs

    def validate_project(self, project):
        request = self.context["request"]
        if not request.user.is_superuser and not project.team.memberships.filter(user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this project's team.")
        return project

    def validate_label_ids(self, labels):
        # label_ids maps to `labels` via source=, so DRF passes it through as `labels`
        return labels


class AssignmentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentRule
        fields = [
            "id", "project", "strategy", "label", "target_user",
            "is_active", "priority_order", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        strategy = attrs.get("strategy") or getattr(self.instance, "strategy", None)
        label = attrs.get("label") or getattr(self.instance, "label", None)
        target_user = attrs.get("target_user") or getattr(self.instance, "target_user", None)
        if strategy == AssignmentRule.Strategy.LABEL_BASED and not label:
            raise serializers.ValidationError({"label": "Required for label_based strategy."})
        if strategy == AssignmentRule.Strategy.DEFAULT_ASSIGNEE and not target_user:
            raise serializers.ValidationError({"target_user": "Required for default_assignee strategy."})
        return attrs
