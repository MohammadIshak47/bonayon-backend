"""ENGINE 4: rotation options come from the crop catalog's rotation_after lists (prototype assumptions)."""
import uuid

from sqlalchemy.orm import Session

from app.core.agronomy import ROTATION_EXPLANATION
from app.core.errors import BadRequestError
from app.models import Crop, RotationPlan, User
from app.repositories import audit
from app.repositories import catalog as catalog_repo
from app.repositories import farms as farms_repo


def suggest(db: Session, season_1_crop_id: uuid.UUID) -> list[dict]:
    first = catalog_repo.get_crop(db, season_1_crop_id)
    out = []
    for cid in first.rotation_after:
        try:
            nxt = db.get(Crop, uuid.UUID(cid))
        except ValueError:
            continue
        if nxt is not None and nxt.is_active:
            out.append({"crop_id": nxt.id, "name_en": nxt.name_en, "name_bn": nxt.name_bn, "explanation": ROTATION_EXPLANATION.format(prev=first.name_en)})
    return out


def save_plan(db: Session, user: User, plot_id: uuid.UUID, c1: uuid.UUID, c2: uuid.UUID, note: str | None) -> RotationPlan:
    farms_repo.get_owned_plot(db, plot_id, user)  # 403 if not the owner
    first = catalog_repo.get_crop(db, c1)
    catalog_repo.get_crop(db, c2)
    if str(c2) not in first.rotation_after:
        raise BadRequestError("That crop is not a listed next-season option after the first crop.")
    plan = RotationPlan(user_id=user.id, plot_id=plot_id, season_1_crop_id=c1, season_2_crop_id=c2, note=note)
    db.add(plan)
    db.commit()
    audit.log(db, user.id, "rotation_plan.create", "rotation_plan", plan.id)
    return plan
