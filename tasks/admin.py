from django.contrib import admin
from tasks.models import Task, AssignmentRule


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "priority", "assignee", "due_date")
    list_filter = ("status", "priority", "project__team__workspace")
    search_fields = ("title", "description")
    autocomplete_fields = ["assignee", "created_by"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("project", "assignee")
        if request.user.is_superuser:
            return qs
        return qs.filter(project__team__workspace__memberships__user=request.user).distinct()


@admin.register(AssignmentRule)
class AssignmentRuleAdmin(admin.ModelAdmin):
    list_display = ("project", "strategy", "label", "target_user", "is_active", "priority_order")
    list_filter = ("strategy", "is_active")
