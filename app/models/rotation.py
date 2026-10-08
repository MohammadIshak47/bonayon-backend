import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDMixin


class RotationPlan(UUIDMixin, Base):
    __tablename__ = "rotation_plans"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plots.id", ondelete="CASCADE"))
    season_1_crop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crops.id"))
    season_2_crop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crops.id"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
