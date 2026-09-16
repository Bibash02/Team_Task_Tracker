from django.contrib import admin
from teams.models import Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "created_at")
    list_filter = ("workspace",)
    search_fields = ("name",)
    inlines = [TeamMembershipInline]

    def get_queryset(self, request):
        # Even in the admin, non-superusers should only see teams in their workspaces.
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(workspace__memberships__user=request.user).distinct()


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "created_at")
    list_filter = ("role", "team__workspace")
