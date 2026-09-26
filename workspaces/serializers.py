from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Workspace, WorkspaceMembership

User = get_user_model()

class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source = 'user.username', read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = ['id', 'workspace', 'user', 'username', 'role', 'created_at']
        read_only_fields = ['id', 'created_at', 'user', 'workspace']

class WorkspaceSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'slug', 'owner', 'member_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'owner', 'member_count', 'created_at', 'updated_at']

class WorkspaceMemberAddSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(choices=WorkspaceMembership.Role.choices, default=WorkspaceMembership.Role.MEMBER)

    def validate_username(self, value):
        try:
            self.user = User.objects.get(username = value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No such user.")
        return value
    