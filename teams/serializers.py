from django.contrib.auth import get_user_model
from rest_framework import serializers
from teams.models import Team, TeamMembership

User = get_user_model()


class TeamMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TeamMembership
        fields = ["id", "team", "user", "username", "role", "created_at"]
        read_only_fields = ["id", "created_at"]


class TeamSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Team
        fields = ["id", "workspace", "name", "description", "member_count", "created_at", "updated_at"]
        read_only_fields = ["id", "member_count", "created_at", "updated_at"]

    def validate_workspace(self, workspace):
        request = self.context["request"]
        if request.user.is_superuser:
            return workspace
        if not workspace.memberships.filter(user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this workspace.")
        return workspace


class TeamMemberAddSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(choices=TeamMembership.Role.choices, default=TeamMembership.Role.MEMBER)

    def validate_username(self, value):
        try:
            self.user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No such user.")
        return value
