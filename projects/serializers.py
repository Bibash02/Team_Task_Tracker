from rest_framework import serializers
from projects.models import Project


class ProjectListSerializer(serializers.ModelSerializer):
    """Lean serializer for list views — no heavy nested data."""
    team_name = serializers.CharField(source="team.name", read_only=True)
    task_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = ["id", "team", "team_name", "name", "status", "task_count", "created_at"]


class ProjectDetailSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "team", "team_name", "name", "description", "status",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_team(self, team):
        request = self.context["request"]
        if not request.user.is_superuser and not team.memberships.filter(user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this team.")
        return team
