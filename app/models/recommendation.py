import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDMixin


class RecommendationType(str, enum.Enum):
    crop_choice = "crop_choice"
    season_plan = "season_plan"


class Recommendation(UUIDMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_user_created", "user_id", "created_at"),)  # history list, newest first
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plots.id", ondelete="SET NULL"))
    type: Mapped[RecommendationType] = mapped_column(Enum(RecommendationType, name="recommendation_type"))
    district_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("districts.id"))
    season: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSONB)          # the engine output, stored as it was shown
    explanations: Mapped[list] = mapped_column(JSONB)
    advisory_text: Mapped[str | None] = mapped_column(Text)
    disclaimer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
