from django.db import models
from common.models import TimeStampedModel
from workspaces.models import Workspace

class Label(TimeStampedModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#808080", help_text="Hex color, e.g. #FF5733")

    class Meta(TimeStampedModel.Meta):
        unique_together = ("workspace", "name")

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"
