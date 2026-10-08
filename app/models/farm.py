import enum
import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin


class SoilType(str, enum.Enum):
    clay = "clay"
    clay_loam = "clay_loam"
    sandy_loam = "sandy_loam"
    sandy = "sandy"
    silt_loam = "silt_loam"
    peat = "peat"


class Farm(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "farms"
    # index on user_id: "my farms" is the hottest query; CASCADE removes a user's farms with the user.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    district_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("districts.id"))
    upazila: Mapped[str | None] = mapped_column(String(80))
    plots: Mapped[list["Plot"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class Plot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "plots"
    __table_args__ = (CheckConstraint("area_decimal > 0", name="ck_plot_area_positive"),)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    area_decimal: Mapped[float] = mapped_column(Float)  # 1 decimal (শতক) = 40.47 m²
    soil_type: Mapped[SoilType] = mapped_column(Enum(SoilType, name="soil_type"))
    crop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crops.id", ondelete="SET NULL"))
    planting_date: Mapped[date | None] = mapped_column(Date)
    season: Mapped[str | None] = mapped_column(String(20))
