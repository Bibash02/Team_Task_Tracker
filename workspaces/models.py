from django.db import models
from django.conf import settings
from django.utils.text import slugify
from common.models import TimeStampedModel

# Create your models here.
class Workspace(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    ownder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_workspaces')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='WorkspaceMembership', related_name='workspaces')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class WorkspaceMembership(TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", 'Member'

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta(TimeStampedModel.Meta):
        unique_together = ("workspace", "user")

    def __str__(self):
        return f"{self.user} @ {self.workspaces} ({self.role})"