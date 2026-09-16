"""
Assignment rule engine.

apply_assignment_rules(task) is called right after a Task is created with
no assignee. It walks the project's active AssignmentRules in order and
stops at the first one that produces an assignee.
"""
from itertools import cycle


def apply_assignment_rules(task):
    if task.assignee_id is not None:
        return task

    rules = task.project.assignment_rules.filter(is_active=True).order_by("priority_order")
    for rule in rules:
        assignee = _evaluate_rule(rule, task)
        if assignee is not None:
            task.assignee = assignee
            task.save(update_fields=["assignee"])
            break
    return task


def _evaluate_rule(rule, task):
    from tasks.models import AssignmentRule

    if rule.strategy == AssignmentRule.Strategy.LABEL_BASED:
        if rule.label_id and task.labels.filter(pk=rule.label_id).exists():
            return rule.target_user
        return None

    if rule.strategy == AssignmentRule.Strategy.DEFAULT_ASSIGNEE:
        return rule.target_user

    if rule.strategy == AssignmentRule.Strategy.LEAST_LOADED:
        return _least_loaded_team_member(rule)

    if rule.strategy == AssignmentRule.Strategy.ROUND_ROBIN:
        return _round_robin_team_member(rule)

    return None


def _team_members(rule):
    return list(rule.team.members.all().order_by("id"))


def _least_loaded_team_member(rule):
    from django.db.models import Count, Q
    from tasks.models import Task

    open_statuses = [Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW]
    members = rule.team.members.annotate(
        open_task_count=Count(
            "assigned_tasks",
            filter=Q(assigned_tasks__status__in=open_statuses),
        )
    ).order_by("open_task_count", "id")
    return members.first()


def _round_robin_team_member(rule):
    """
    Naive round robin: pick whichever team member has the fewest tasks
    assigned from THIS rule's project, tie-broken by user id. This keeps
    it deterministic and stateless (no extra "last assigned" table needed).
    """
    from django.db.models import Count, Q

    members = rule.team.members.annotate(
        project_task_count=Count("assigned_tasks", filter=Q(assigned_tasks__project=rule.project))
    ).order_by("project_task_count", "id")
    return members.first()
