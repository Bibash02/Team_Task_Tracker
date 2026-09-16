"""
Queryset-scoping mixins.

This is the piece that makes the "workspace boundary" rule actually hold
everywhere, instead of relying on every view author to remember to filter.
Every viewset that touches workspace-owned data mixes this in and declares
`workspace_lookup` (the ORM path from the model to Workspace). Combined
with `IsWorkspaceMember` object permission, this gives defense in depth:
the queryset never returns rows outside the user's workspaces, and even if
a PK from outside the boundary was guessed, the object-permission check on
retrieve/update/delete blocks it.
"""


class WorkspaceScopedQuerysetMixin:
    """
    workspace_lookup: ORM path (using __) from the model to the Workspace's
    membership relation. Examples:
      - Workspace itself:            ""  (special-cased below)
      - Team (fk to Workspace):      "workspace"
      - Project (fk to Team):        "team__workspace"
      - Task (fk to Project):        "project__team__workspace"
      - Comment (fk to Task):        "task__project__team__workspace"
      - Label (fk to Workspace):     "workspace"
    """
    workspace_lookup = ""
    # Extra select_related/prefetch_related applied unconditionally,
    # so scoping never becomes an added N+1 query source.
    select_related_fields = ()
    prefetch_related_fields = ()

    def get_base_queryset(self):
        return super().get_queryset()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.get_base_queryset().none()

        qs = self.get_base_queryset()
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)

        user = self.request.user
        if user.is_superuser:
            return qs

        if self.workspace_lookup:
            filter_kwargs = {f"{self.workspace_lookup}__memberships__user": user}
        else:
            # The model itself IS Workspace
            filter_kwargs = {"memberships__user": user}
        return qs.filter(**filter_kwargs).distinct()


class TeamScopedQuerysetMixin:
    """
    Same idea as WorkspaceScopedQuerysetMixin but scoped at the team level,
    for endpoints where workspace membership alone is too coarse (e.g. a
    workspace member who isn't on the relevant team shouldn't see its
    private project tasks in a "team-only" view).
    """
    team_lookup = ""
    select_related_fields = ()
    prefetch_related_fields = ()

    def get_base_queryset(self):
        return super().get_queryset()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.get_base_queryset().none()

        qs = self.get_base_queryset()
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)

        user = self.request.user
        if user.is_superuser:
            return qs

        prefix = f"{self.team_lookup}__" if self.team_lookup else ""
        filter_kwargs = {f"{prefix}memberships__user": user}
        return qs.filter(**filter_kwargs).distinct()


class CreatedByMixin:
    """Auto-fill created_by / author fields from request.user on create."""
    created_by_field = "created_by"

    def perform_create(self, serializer):
        serializer.save(**{self.created_by_field: self.request.user})
