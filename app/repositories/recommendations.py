from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Recommendation, RecommendationType, User
from app.utils.pagination import paginate


def add(db: Session, **fields) -> Recommendation:
    rec = Recommendation(**fields)
    db.add(rec)
    db.commit()
    return rec


def history(db: Session, user: User, rec_type: RecommendationType | None, page: int, size: int):
    stmt = select(Recommendation).where(Recommendation.user_id == user.id).order_by(Recommendation.created_at.desc())
    if rec_type:
        stmt = stmt.where(Recommendation.type == rec_type)
    return paginate(db, stmt, page, size)


def count_plans(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).select_from(Recommendation).where(
        Recommendation.user_id == user.id, Recommendation.type == RecommendationType.season_plan)) or 0
