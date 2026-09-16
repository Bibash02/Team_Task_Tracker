from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import WorkspaceScopedQuerysetMixin, CreatedByMixin
from common.permissions import IsWorkspaceMember, IsTeamLeadOrWorkspaceAdmin
from audit.utils import log_event
from audit.models import AuditEvent
from tasks.models import Task, AssignmentRule
from tasks.serializers import TaskListSerializer, TaskDetailSerializer, AssignmentRuleSerializer
from tasks.filters import TaskFilter
from tasks.services import apply_assignment_rules


class TaskViewSet(WorkspaceScopedQuerysetMixin, CreatedByMixin, viewsets.ModelViewSet):
    """
    The whole point of the exercise lives here: a workspace member only
    ever sees tasks whose project->team->workspace they belong to. That's
    enforced at the queryset level (WorkspaceScopedQuerysetMixin) AND at
    the object level (IsWorkspaceMember.has_object_permission), so a
    guessed task UUID from another workspace 404s, it doesn't 403 (avoids
    leaking existence).
    """
    permission_classes = [IsWorkspaceMember]
    workspace_lookup = "project__team__workspace"
    select_related_fields = ("project", "project__team", "project__team__workspace", "assignee", "created_by")
    prefetch_related_fields = ("labels",)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TaskFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "due_date", "priority"]
    ordering = ["-created_at"]

    def get_base_queryset(self):
        qs = Task.objects.all()
        if self.action == "retrieve":
            qs = qs.annotate(comment_count=Count("comments", distinct=True))
        return qs

    def get_serializer_class(self):
        return TaskListSerializer if self.action == "list" else TaskDetailSerializer

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        apply_assignment_rules(task)
        log_event(
            workspace=task.workspace, actor=self.request.user, action=AuditEvent.Action.CREATE,
            target=task, description=f"Task '{task.title}' created in project '{task.project.name}'",
        )
        if task.assignee_id:
            log_event(
                workspace=task.workspace, actor=self.request.user, action=AuditEvent.Action.ASSIGN,
                target=task, description=f"Task '{task.title}' auto-assigned to {task.assignee.username}",
            )

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        old_assignee_id = serializer.instance.assignee_id
        task = serializer.save()

        if task.status != old_status:
            log_event(
                workspace=task.workspace, actor=self.request.user, action=AuditEvent.Action.STATUS_CHANGE,
                target=task, description=f"Task '{task.title}' status: {old_status} -> {task.status}",
                metadata={"old_status": old_status, "new_status": task.status},
            )
        if task.assignee_id != old_assignee_id:
            log_event(
                workspace=task.workspace, actor=self.request.user, action=AuditEvent.Action.ASSIGN,
                target=task,
                description=f"Task '{task.title}' reassigned to "
                             f"{task.assignee.username if task.assignee else 'nobody'}",
                metadata={"old_assignee_id": old_assignee_id, "new_assignee_id": task.assignee_id},
            )
        if task.status == old_status and task.assignee_id == old_assignee_id:
            log_event(
                workspace=task.workspace, actor=self.request.user, action=AuditEvent.Action.UPDATE,
                target=task, description=f"Task '{task.title}' updated",
            )

    def perform_destroy(self, instance):
        log_event(
            workspace=instance.workspace, actor=self.request.user, action=AuditEvent.Action.DELETE,
            target=instance, description=f"Task '{instance.title}' deleted",
        )
        super().perform_destroy(instance)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        """Convenience endpoint: PATCH /api/tasks/{id}/status/ {"status": "done"}"""
        task = self.get_object()
        new_status = request.data.get("status")
        if new_status not in Task.Status.values:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        old_status = task.status
        task.status = new_status
        task.save(update_fields=["status"])
        log_event(
            workspace=task.workspace, actor=request.user, action=AuditEvent.Action.STATUS_CHANGE,
            target=task, description=f"Task '{task.title}' status: {old_status} -> {new_status}",
        )
        return Response(TaskDetailSerializer(task, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        """PATCH /api/tasks/{id}/assign/ {"assignee": <user_id>}"""
        task = self.get_object()
        assignee_id = request.data.get("assignee")
        if assignee_id is None:
            task.assignee = None
        else:
            if not task.team.memberships.filter(user_id=assignee_id).exists():
                return Response(
                    {"detail": "Assignee must be a member of the task's team."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            task.assignee_id = assignee_id
        task.save(update_fields=["assignee"])
        log_event(
            workspace=task.workspace, actor=request.user, action=AuditEvent.Action.ASSIGN,
            target=task,
            description=f"Task '{task.title}' assigned to "
                         f"{task.assignee.username if task.assignee else 'nobody'}",
        )
        return Response(TaskDetailSerializer(task, context={"request": request}).data)


class AssignmentRuleViewSet(WorkspaceScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = AssignmentRuleSerializer
    permission_classes = [IsWorkspaceMember]
    workspace_lookup = "project__team__workspace"
    select_related_fields = ("project", "project__team__workspace", "label", "target_user")
    filterset_fields = ["project", "strategy", "is_active"]

    def get_base_queryset(self):
        return AssignmentRule.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [p() for p in [IsTeamLeadOrWorkspaceAdmin]]
        return super().get_permissions()

    def perform_create(self, serializer):
        rule = serializer.save()
        log_event(
            workspace=rule.workspace, actor=self.request.user, action=AuditEvent.Action.CREATE,
            target=rule, description=f"Assignment rule ({rule.strategy}) created for '{rule.project.name}'",
        )
