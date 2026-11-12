from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AdminAuditLog, User

router = APIRouter(prefix="/api/admin", tags=["Yönetim"])


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=80),
    resource_type: str | None = Query(default=None, max_length=80),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Yalnızca yönetici denetim kayıtlarını görüntüleyebilir.")
    query = select(AdminAuditLog)
    if action:
        query = query.where(AdminAuditLog.action == action)
    if resource_type:
        query = query.where(AdminAuditLog.resource_type == resource_type)
    rows = db.scalars(
        query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return [{
        "id": str(row.id),
        "actor_id": str(row.actor_id) if row.actor_id else None,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "summary": row.summary,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]
