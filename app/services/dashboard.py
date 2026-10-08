from sqlalchemy.orm import Session

from app.models import User
from app.repositories import farms as farms_repo
from app.repositories import recommendations as rec_repo


def build(db: Session, user: User) -> dict:
    farms, plots = farms_repo.counts(db, user)
    recent, _ = rec_repo.history(db, user, None, 1, 5)
    return {"farms_count": farms, "plots_count": plots, "plans_count": rec_repo.count_plans(db, user),
            "latest_recommendation": recent[0] if recent else None, "recent_recommendations": recent}
