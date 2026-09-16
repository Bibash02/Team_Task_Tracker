from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from workspaces.models import Workspace
from projects.models import Project
from tasks.models import Task


class DashboardView(APIView):
    """
    GET /api/dashboard/                       -> stats across all of the caller's workspaces
    GET /api/dashboard/?workspace=<id>         -> stats scoped to one workspace

    Every number here comes from a handful of aggregate()/annotate() calls
    against the already-workspace-scoped querysets — there is no per-row
    Python loop, so this stays O(1) queries regardless of how many tasks
    exist.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = None  # plain aggregate response, documented via SPECTACULAR extend_schema if needed

    def get(self, request):
        user = request.user

        if user.is_superuser:
            workspaces = Workspace.objects.all()
        else:
            workspaces = Workspace.objects.filter(memberships__user=user).distinct()

        workspace_id = request.query_params.get("workspace")
        if workspace_id:
            workspaces = workspaces.filter(id=workspace_id)

        projects = Project.objects.filter(team__workspace__in=workspaces)
        tasks = Task.objects.filter(project__team__workspace__in=workspaces)

        status_counts = tasks.aggregate(
            todo=Count("id", filter=Q(status=Task.Status.TODO)),
            in_progress=Count("id", filter=Q(status=Task.Status.IN_PROGRESS)),
            in_review=Count("id", filter=Q(status=Task.Status.IN_REVIEW)),
            completed=Count("id", filter=Q(status=Task.Status.DONE)),
            cancelled=Count("id", filter=Q(status=Task.Status.CANCELLED)),
            overdue=Count(
                "id",
                filter=Q(due_date__lt=timezone.localdate()) & ~Q(status=Task.Status.DONE) & ~Q(status=Task.Status.CANCELLED),
            ),
        )

        by_priority = {
            row["priority"]: row["count"]
            for row in tasks.values("priority").annotate(count=Count("id")).order_by("priority")
        }

        by_assignee = list(
            tasks.exclude(assignee__isnull=True)
            .values("assignee_id", "assignee__username")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        data = {
            "total_workspaces": workspaces.count(),
            "total_projects": projects.count(),
            "total_tasks": tasks.count(),
            "todo": status_counts["todo"],
            "in_progress": status_counts["in_progress"],
            "in_review": status_counts["in_review"],
            "completed": status_counts["completed"],
            "cancelled": status_counts["cancelled"],
            "overdue": status_counts["overdue"],
            "tasks_by_priority": by_priority,
            "tasks_by_assignee": [
                {
                    "assignee_id": row["assignee_id"],
                    "username": row["assignee__username"],
                    "count": row["count"],
                }
                for row in by_assignee
            ],
        }
        return Response(data)
