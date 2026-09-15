from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.mixins import WorkspaceScopedQuerysetMixin
from common.permissions import IsWorkspaceMember, IsWorkspaceAdmin
from audit.utils import log_event
from audit.models import AuditEvent
from workspaces.models import Workspace, WorkspaceMembership
from workspaces.serializers import (
    WorkspaceSerializer, WorkspaceMembershipSerializer, WorkspaceMemberAddSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    Workspace is the tenant root. list/retrieve are scoped to workspaces
    the user belongs to; create is open to any authenticated user (they
    become owner + admin); membership management requires workspace admin.
    """
    serializer_class = WorkspaceSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Workspace.objects.none()
        qs = Workspace.objects.annotate(member_count=Count("memberships", distinct=True)).order_by("-created_at")
        if self.request.user.is_superuser:
            return qs
        return qs.filter(memberships__user=self.request.user).distinct()

    def get_permissions(self):
        if self.action == "create":
            return [p() for p in [IsWorkspaceMember]]  # just IsAuthenticated in effect (has_permission only)
        if self.action in ("add_member", "remove_member", "destroy"):
            return [p() for p in [IsWorkspaceAdmin]]
        return super().get_permissions()

    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        WorkspaceMembership.objects.create(
            workspace=workspace, user=self.request.user, role=WorkspaceMembership.Role.ADMIN
        )
        log_event(
            workspace=workspace, actor=self.request.user, action=AuditEvent.Action.CREATE,
            target=workspace, description=f"Workspace '{workspace.name}' created",
        )

    @action(detail=True, methods=["post"], url_path="members")
    def add_member(self, request, pk=None):
        workspace = self.get_object()
        self.check_object_permissions(request, workspace)
        serializer = WorkspaceMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, created = WorkspaceMembership.objects.get_or_create(
            workspace=workspace, user=serializer.user,
            defaults={"role": serializer.validated_data["role"]},
        )
        if not created:
            return Response({"detail": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)
        log_event(
            workspace=workspace, actor=request.user, action=AuditEvent.Action.MEMBER_ADD,
            target=membership, description=f"{serializer.user.username} added to workspace",
        )
        return Response(WorkspaceMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        workspace = self.get_object()
        self.check_object_permissions(request, workspace)
        try:
            membership = WorkspaceMembership.objects.get(workspace=workspace, user_id=user_id)
        except WorkspaceMembership.DoesNotExist:
            return Response({"detail": "Not a member."}, status=status.HTTP_404_NOT_FOUND)
        if membership.user_id == workspace.owner_id:
            return Response({"detail": "Cannot remove the workspace owner."}, status=status.HTTP_400_BAD_REQUEST)
        username = membership.user.username
        membership.delete()
        log_event(
            workspace=workspace, actor=request.user, action=AuditEvent.Action.MEMBER_REMOVE,
            target=workspace, description=f"{username} removed from workspace",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="members")
    def list_members(self, request, pk=None):
        workspace = self.get_object()
        memberships = workspace.memberships.select_related("user").all()
        return Response(WorkspaceMembershipSerializer(memberships, many=True).data)


class MembershipViewSet(viewsets.ModelViewSet):
    """
    Top-level /api/memberships/ endpoint (as opposed to the nested
    /api/workspaces/{id}/members/ actions above). list/retrieve are scoped
    to the caller's own workspaces; role changes and removal require
    workspace admin. Creation of new memberships should go through
    /api/workspaces/{id}/members/ (it validates the target user exists),
    this endpoint mainly supports viewing + role updates + removal.
    """
    serializer_class = WorkspaceMembershipSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WorkspaceMembership.objects.none()
        qs = WorkspaceMembership.objects.select_related("workspace", "user")
        if self.request.user.is_superuser:
            return qs
        return qs.filter(workspace__memberships__user=self.request.user).distinct()

    def get_permissions(self):
        if self.action in ("partial_update", "update", "destroy"):
            return [p() for p in [IsWorkspaceAdmin]]
        return [p() for p in [IsWorkspaceMember]]

    def perform_update(self, serializer):
        old_role = serializer.instance.role
        membership = serializer.save()
        if membership.role != old_role:
            log_event(
                workspace=membership.workspace, actor=self.request.user, action=AuditEvent.Action.ROLE_CHANGE,
                target=membership,
                description=f"{membership.user.username} role: {old_role} -> {membership.role}",
            )

    def perform_destroy(self, instance):
        if instance.user_id == instance.workspace.owner_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot remove the workspace owner.")
        log_event(
            workspace=instance.workspace, actor=self.request.user, action=AuditEvent.Action.MEMBER_REMOVE,
            target=instance.workspace, description=f"{instance.user.username} removed from workspace",
        )
        super().perform_destroy(instance)
