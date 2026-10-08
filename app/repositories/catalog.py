import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Crop, District


def list_districts(db: Session) -> list[District]:
    return list(db.scalars(select(District).order_by(District.name_en)))


def get_district(db: Session, district_id: uuid.UUID) -> District:
    d = db.get(District, district_id)
    if d is None:
        raise NotFoundError("District not found")
    return d


def list_crops(db: Session, active_only: bool = True) -> list[Crop]:
    stmt = select(Crop).order_by(Crop.name_en)
    if active_only:
        stmt = stmt.where(Crop.is_active.is_(True))
    return list(db.scalars(stmt))


def get_crop(db: Session, crop_id: uuid.UUID) -> Crop:
    c = db.get(Crop, crop_id)
    if c is None:
        raise NotFoundError("Crop not found")
    return c
