from rest_framework import permissions

def _resolve_workspace(obj):
    pass

def _resolve_team(obj):
    pass

class IsAuthenticatedAndActive(permissions.BasePermission):
    pass

class IsWorkspaceMember(permissions.BasePermission):
    pass

class IsTeamMember(permissions.BasePermission):
    pass

class IsWorkspaceAdmin(permissions.BasePermission):
    pass    

class IsTeamLeadOrWorkspaceAdmin(permissions.BasePermission):
    pass

class IsCommonAuthorOrReadOnly(permissions.BasePermission):
    pass