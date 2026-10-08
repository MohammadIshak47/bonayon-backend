import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import User
from app.utils.pagination import paginate


def get(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create(db: Session, **fields) -> User:
    user = User(**fields)
    db.add(user)
    db.commit()
    return user


def search(db: Session, query: str | None, page: int, size: int):
    stmt = select(User).order_by(User.created_at.desc())
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.name.ilike(like)))
    return paginate(db, stmt, page, size)
