from django.db.models import Count
from rest_framework import viewsets

from common.mixins import WorkspaceScopedQuerysetMixin, CreatedByMixin
from common.permissions import IsWorkspaceMember, IsTeamLeadOrWorkspaceAdmin
from audit.utils import log_event
from audit.models import AuditEvent
from projects.models import Project
from projects.serializers import ProjectListSerializer, ProjectDetailSerializer


class ProjectViewSet(WorkspaceScopedQuerysetMixin, CreatedByMixin, viewsets.ModelViewSet):
    permission_classes = [IsWorkspaceMember]
    workspace_lookup = "team__workspace"
    select_related_fields = ("team", "team__workspace")
    filterset_fields = ["team", "status"]

    def get_base_queryset(self):
        return Project.objects.annotate(task_count=Count("tasks", distinct=True)).order_by("-created_at")

    def get_serializer_class(self):
        return ProjectListSerializer if self.action == "list" else ProjectDetailSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [p() for p in [IsTeamLeadOrWorkspaceAdmin]]
        return super().get_permissions()

    def perform_create(self, serializer):
        project = serializer.save(created_by=self.request.user)
        log_event(
            workspace=project.workspace, actor=self.request.user, action=AuditEvent.Action.CREATE,
            target=project, description=f"Project '{project.name}' created in team '{project.team.name}'",
        )

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        project = serializer.save()
        if project.status != old_status:
            log_event(
                workspace=project.workspace, actor=self.request.user, action=AuditEvent.Action.STATUS_CHANGE,
                target=project, description=f"Project '{project.name}' status: {old_status} -> {project.status}",
            )
        else:
            log_event(
                workspace=project.workspace, actor=self.request.user, action=AuditEvent.Action.UPDATE,
                target=project, description=f"Project '{project.name}' updated",
            )

    def perform_destroy(self, instance):
        log_event(
            workspace=instance.workspace, actor=self.request.user, action=AuditEvent.Action.DELETE,
            target=instance, description=f"Project '{instance.name}' deleted",
        )
        super().perform_destroy(instance)
