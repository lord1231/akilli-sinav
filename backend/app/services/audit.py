from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AdminAuditLog, User


def record_admin_action(
    db: Session,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    summary: str = "",
) -> None:
    """Add a minimal audit event to the caller's transaction; never store secrets or payloads."""
    if actor.role != "admin":
        return
    db.add(AdminAuditLog(
        actor_id=actor.id,
        action=action[:80],
        resource_type=resource_type[:80],
        resource_id=str(resource_id)[:80] if resource_id is not None else None,
        summary=summary[:500],
    ))
