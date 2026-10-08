import enum
import uuid  # noqa: F401

from sqlalchemy import ARRAY, Boolean, CheckConstraint, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDMixin


class WaterSensitivity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Crop(UUIDMixin, TimestampMixin, Base):
    """Reference catalog. Ranges are FAO-informed PROTOTYPE ASSUMPTIONS (see app/core/agronomy.py)."""
    __tablename__ = "crops"
    __table_args__ = (
        CheckConstraint("rain_max_mm > rain_min_mm", name="ck_crop_rain_range"),  # a range must have positive width
        CheckConstraint("temp_max_c > temp_min_c", name="ck_crop_temp_range"),
        CheckConstraint("seed_kg_per_decimal > 0", name="ck_crop_seed_positive"),
    )
    name_en: Mapped[str] = mapped_column(String(80), unique=True)
    name_bn: Mapped[str] = mapped_column(String(80))
    seasons: Mapped[list[str]] = mapped_column(ARRAY(String))
    rain_min_mm: Mapped[float] = mapped_column(Float)
    rain_max_mm: Mapped[float] = mapped_column(Float)
    temp_min_c: Mapped[float] = mapped_column(Float)
    temp_max_c: Mapped[float] = mapped_column(Float)
    suitable_soils: Mapped[list[str]] = mapped_column(ARRAY(String))
    water_sensitivity: Mapped[WaterSensitivity] = mapped_column(Enum(WaterSensitivity, name="water_sensitivity"))
    rotation_after: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)  # crop ids (as text) suitable next season
    seed_kg_per_decimal: Mapped[float] = mapped_column(Float)
    npk_note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
