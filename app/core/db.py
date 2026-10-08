from collections.abc import Iterator
import uuid
from datetime import datetime

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings

# pool_pre_ping + pool_recycle: Neon suspends idle compute and closes idle connections, so stale ones are replaced.
# prepare_threshold=None: no server-side prepared statements, which keeps this working through Neon's pooled
# ("-pooler", PgBouncer) connection string as well as the direct one.
engine = create_engine(
    get_settings().DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    # UUID primary keys (uuid4): not guessable/enumerable like serial integers.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
