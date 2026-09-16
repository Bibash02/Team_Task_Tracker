from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.mixins import WorkspaceScopedQuerysetMixin
from common.permissions import IsWorkspaceMember, IsTeamLeadOrWorkspaceAdmin
from audit.utils import log_event
from audit.models import AuditEvent
from teams.models import Team, TeamMembership
from teams.serializers import TeamSerializer, TeamMembershipSerializer, TeamMemberAddSerializer
from workspaces.models import WorkspaceMembership


class TeamViewSet(WorkspaceScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    A user only ever sees teams belonging to workspaces they are a member
    of (enforced by WorkspaceScopedQuerysetMixin). Optionally filter to
    "my teams" with ?mine=1.
    """
    serializer_class = TeamSerializer
    permission_classes = [IsWorkspaceMember]
    workspace_lookup = "workspace"
    select_related_fields = ("workspace",)

    def get_base_queryset(self):
        return Team.objects.annotate(member_count=Count("memberships", distinct=True))

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("mine") == "1":
            qs = qs.filter(memberships__user=self.request.user)
        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        return qs.distinct()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        return ctx

    def get_permissions(self):
        if self.action in ("add_member", "remove_member", "update", "partial_update", "destroy"):
            return [p() for p in [IsTeamLeadOrWorkspaceAdmin]]
        return super().get_permissions()

    def perform_create(self, serializer):
        team = serializer.save()
        # Creator becomes team lead automatically.
        TeamMembership.objects.create(team=team, user=self.request.user, role=TeamMembership.Role.LEAD)
        log_event(
            workspace=team.workspace, actor=self.request.user, action=AuditEvent.Action.CREATE,
            target=team, description=f"Team '{team.name}' created",
        )

    def perform_destroy(self, instance):
        log_event(
            workspace=instance.workspace, actor=self.request.user, action=AuditEvent.Action.DELETE,
            target=instance, description=f"Team '{instance.name}' deleted",
        )
        super().perform_destroy(instance)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        team = self.get_object()
        if request.method == "GET":
            memberships = team.memberships.select_related("user").all()
            return Response(TeamMembershipSerializer(memberships, many=True).data)

        self.check_object_permissions(request, team)
        serializer = TeamMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Must already be a workspace member before joining a team.
        if not WorkspaceMembership.objects.filter(workspace=team.workspace, user=serializer.user).exists():
            return Response(
                {"detail": "User must join the workspace before joining a team."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership, created = TeamMembership.objects.get_or_create(
            team=team, user=serializer.user, defaults={"role": serializer.validated_data["role"]},
        )
        if not created:
            return Response({"detail": "User is already on this team."}, status=status.HTTP_400_BAD_REQUEST)
        log_event(
            workspace=team.workspace, actor=request.user, action=AuditEvent.Action.MEMBER_ADD,
            target=membership, description=f"{serializer.user.username} added to team '{team.name}'",
        )
        return Response(TeamMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        team = self.get_object()
        self.check_object_permissions(request, team)
        try:
            membership = TeamMembership.objects.get(team=team, user_id=user_id)
        except TeamMembership.DoesNotExist:
            return Response({"detail": "Not a member."}, status=status.HTTP_404_NOT_FOUND)
        username = membership.user.username
        membership.delete()
        log_event(
            workspace=team.workspace, actor=request.user, action=AuditEvent.Action.MEMBER_REMOVE,
            target=team, description=f"{username} removed from team '{team.name}'",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
