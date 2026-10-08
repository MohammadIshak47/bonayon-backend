import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.utils.pagination import paginate


def log(db: Session, user_id: uuid.UUID | None, action: str, entity: str, entity_id: uuid.UUID | None = None, meta: dict | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity=entity, entity_id=entity_id, meta=meta))
    db.commit()


def list_logs(db: Session, page: int, size: int):
    return paginate(db, select(AuditLog).order_by(AuditLog.created_at.desc()), page, size)
