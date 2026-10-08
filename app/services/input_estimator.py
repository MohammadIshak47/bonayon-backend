"""ENGINE 5: seed quantity = area x catalog seed rate. NPK text is the catalog note. Always labeled an estimate."""
import uuid

from sqlalchemy.orm import Session

from app.core.agronomy import ESTIMATE_LABEL
from app.repositories import catalog as catalog_repo


def estimate(db: Session, crop_id: uuid.UUID, area_decimal: float) -> dict:
    crop = catalog_repo.get_crop(db, crop_id)
    return {"crop_id": crop.id, "crop_name": crop.name_en, "area_decimal": area_decimal,
            "seed_kg": round(area_decimal * crop.seed_kg_per_decimal, 3), "npk_note": crop.npk_note, "label": ESTIMATE_LABEL}
