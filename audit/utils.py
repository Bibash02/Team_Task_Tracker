"""
log_event() is the single entry point every app uses to write an audit
trail row. Keeping it here (rather than scattering AuditEvent.objects.create
calls) means the shape of an audit record only needs to change in one place.
"""
from audit.models import AuditEvent


def log_event(*, workspace, actor, action, target, description, metadata=None):
    AuditEvent.objects.create(
        workspace=workspace,
        actor=actor if (actor and getattr(actor, "is_authenticated", True)) else None,
        action=action,
        target_type=target.__class__.__name__.lower(),
        target_id=str(target.pk),
        description=description,
        metadata=metadata or {},
    )
