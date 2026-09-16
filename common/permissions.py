"""
Central object-level permission classes.

Design: every model that lives inside the workspace hierarchy exposes a
`.workspace` property (directly, or via team/project). These permission
classes rely purely on that contract, so they work identically for Team,
Project, Task, Comment, Label, etc. without per-model subclasses.
"""
from rest_framework import permissions


def _resolve_workspace(obj):
    """Return the Workspace instance an object belongs to."""
    # Workspace itself
    if obj.__class__.__name__ == "Workspace":
        return obj
    return getattr(obj, "workspace", None)


def _resolve_team(obj):
    if obj.__class__.__name__ == "Team":
        return obj
    return getattr(obj, "team", None)


class IsAuthenticatedAndActive(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsWorkspaceMember(permissions.BasePermission):
    """
    Object-level check: the requesting user must be a member of the
    object's workspace (or a superuser). This is the permission that
    enforces the core rule: users only ever see/act on data inside
    workspaces (and therefore teams) they belong to.
    """

    message = "You are not a member of this workspace."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        workspace = _resolve_workspace(obj)
        if workspace is None:
            return False
        return workspace.memberships.filter(user=request.user).exists()


class IsTeamMember(permissions.BasePermission):
    """Object-level check restricted to team membership (tighter than workspace)."""

    message = "You are not a member of this team."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        team = _resolve_team(obj)
        if team is None:
            return False
        return team.memberships.filter(user=request.user).exists()


class IsWorkspaceAdmin(permissions.BasePermission):
    """Only workspace admins (or superusers) may perform the action."""

    message = "You must be a workspace admin to do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        workspace = _resolve_workspace(obj)
        if workspace is None:
            return False
        return workspace.memberships.filter(
            user=request.user, role="admin"
        ).exists()


class IsTeamLeadOrWorkspaceAdmin(permissions.BasePermission):
    """Used for write actions on Projects/AssignmentRules: team leads or workspace admins."""

    message = "You must be a team lead or workspace admin to do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        team = _resolve_team(obj)
        workspace = _resolve_workspace(obj)
        is_lead = team and team.memberships.filter(user=request.user, role="lead").exists()
        is_admin = workspace and workspace.memberships.filter(user=request.user, role="admin").exists()
        return bool(is_lead or is_admin)


class IsCommentAuthorOrReadOnly(permissions.BasePermission):
    """Anyone in the workspace can read; only the author (or admin) can edit/delete."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        if obj.author_id == request.user.id:
            return True
        workspace = _resolve_workspace(obj)
        return bool(workspace and workspace.memberships.filter(user=request.user, role="admin").exists())
