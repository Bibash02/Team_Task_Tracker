from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from teams.models import Team

class Project(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        COMPLETED = "completed", "Completed"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_projects"
    )

    class Meta(TimeStampedModel.Meta):
        unique_together = ("team", "name")

    def __str__(self):
        return f"{self.name} [{self.team.name}]"

    @property
    def workspace(self):
        return self.team.workspace
