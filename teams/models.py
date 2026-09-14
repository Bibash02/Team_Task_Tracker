from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
from workspaces.models import Workspace 

# Create your models here.
class Team(TimeStampedModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='teams_teams')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="TeamMembership", related_name='teams_teams')

    class Meta(TimeStampedModel.Meta):
        unique_together = ('workspace', 'name')

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"

class TeamMembership(TimeStampedModel):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        MEMBER = "member", "Member"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memerships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta(TimeStampedModel.Meta):
        unique_together = ('team', 'user')

    def __str__(self):
        return f"{self.user} @ {self.team} ({self.role})"
        