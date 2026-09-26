from django.contrib import admin

from workspaces.models import Workspace, WorkspaceMembership


class WorkspaceMembershipInline(admin.TabularInline):
    model = WorkspaceMembership
    extra = 0


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "member_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "slug", "owner__username")
    inlines = [WorkspaceMembershipInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(memberships__user=request.user).distinct()

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.memberships.count()


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "created_at")
    list_filter = ("role", "workspace")
    search_fields = ("workspace__name", "user__username")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(workspace__memberships__user=request.user).distinct()
