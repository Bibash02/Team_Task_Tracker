import django_filters
from tasks.models import Task


class TaskFilter(django_filters.FilterSet):
    assignee = django_filters.NumberFilter(field_name="assignee_id")
    status = django_filters.ChoiceFilter(choices=Task.Status.choices)
    priority = django_filters.ChoiceFilter(choices=Task.Priority.choices)
    project = django_filters.UUIDFilter(field_name="project_id")
    team = django_filters.UUIDFilter(field_name="project__team_id")
    label = django_filters.UUIDFilter(field_name="labels__id")
    creator = django_filters.NumberFilter(field_name="created_by_id")
    due_date = django_filters.DateFilter(field_name="due_date")
    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    unassigned = django_filters.BooleanFilter(field_name="assignee", lookup_expr="isnull")

    class Meta:
        model = Task
        fields = ["assignee", "status", "priority", "project", "team", "label", "creator", "unassigned"]
