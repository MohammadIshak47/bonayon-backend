import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDMixin


class ClimateRecord(UUIDMixin, Base):
    """Daily climate cache. Value columns are nullable: NASA marks missing days, and we still store the
    date so we never re-request a day the provider has no value for."""
    __tablename__ = "climate_records"
    # UNIQUE(district_id, date) also serves as the (district_id, date) lookup index and makes inserts idempotent.
    __table_args__ = (UniqueConstraint("district_id", "date", name="uq_climate_district_date"),)
    district_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    temp_max: Mapped[float | None] = mapped_column(Float)
    temp_avg: Mapped[float | None] = mapped_column(Float)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    wind_speed: Mapped[float | None] = mapped_column(Float)
    heatwave_day: Mapped[bool] = mapped_column(Boolean, default=False)
    dry_spell: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
