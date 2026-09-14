from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from projects.models import Project
from labels.models import Label


class Task(TimeStampedModel):
    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        IN_REVIEW = "in_review", "In Review"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_tasks"
    )
    labels = models.ManyToManyField(Label, blank=True, related_name="tasks")
    due_date = models.DateField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["assignee", "status"]),
        ]

    def __str__(self):
        return self.title

    @property
    def team(self):
        return self.project.team

    @property
    def workspace(self):
        return self.project.team.workspace


class AssignmentRule(TimeStampedModel):
    class Strategy(models.TextChoices):
        LABEL_BASED = "label_based", "Assign by label"
        DEFAULT_ASSIGNEE = "default_assignee", "Fixed default assignee"
        LEAST_LOADED = "least_loaded", "Least loaded team member"
        ROUND_ROBIN = "round_robin", "Round robin across team"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="assignment_rules")
    strategy = models.CharField(max_length=30, choices=Strategy.choices)
    label = models.ForeignKey(
        Label, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Required for label_based strategy.",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assignment_rule_targets", help_text="Required for default_assignee strategy.",
    )
    is_active = models.BooleanField(default=True)
    priority_order = models.PositiveIntegerField(default=0)

    class Meta(TimeStampedModel.Meta):
        ordering = ["priority_order", "created_at"]

    def __str__(self):
        return f"{self.get_strategy_display()} for {self.project.name}"

    @property
    def workspace(self):
        return self.project.team.workspace

    @property
    def team(self):
        return self.project.team