from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDMixin


class District(UUIDMixin, Base):
    __tablename__ = "districts"
    name_en: Mapped[str] = mapped_column(String(80), unique=True)  # UNIQUE: seed script is idempotent by name
    name_bn: Mapped[str] = mapped_column(String(80))
    division: Mapped[str] = mapped_column(String(40))
    lat: Mapped[float] = mapped_column(Float)  # approximate district HQ, used for NASA POWER queries
    lon: Mapped[float] = mapped_column(Float)
