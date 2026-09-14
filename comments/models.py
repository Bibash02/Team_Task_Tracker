from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from tasks.models import Task

class Comment(TimeStampedModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField()

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["task", "-created_at"])]

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"

    @property
    def workspace(self):
        return self.task.workspace

    @property
    def team(self):
        return self.task.team
