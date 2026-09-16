from rest_framework import viewsets
from common.mixins import WorkspaceScopedQuerysetMixin
from common.permissions import IsWorkspaceMember
from labels.models import Label
from labels.serializers import LabelSerializer


class LabelViewSet(WorkspaceScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = [IsWorkspaceMember]
    workspace_lookup = "workspace"
    select_related_fields = ("workspace",)
    filterset_fields = ["workspace"]

    def get_base_queryset(self):
        return Label.objects.all()
