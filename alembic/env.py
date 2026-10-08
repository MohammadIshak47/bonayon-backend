from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.core.config import get_settings
from app.core.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
URL = get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(url=URL, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(URL)
    try:
        connection = engine.connect()
    except OperationalError as exc:  # a short, actionable message instead of a 100-line traceback
        u = make_url(URL)
        reason = str(exc.orig).strip().splitlines()[0] if exc.orig else str(exc)
        raise SystemExit(
            f"\nCannot connect to PostgreSQL as user '{u.username}' at {u.host or '(local socket)'}:{u.port or 5432}, database '{u.database}'.\n"
            f"Reason: {reason}\n"
            "Check: 1) the PostgreSQL service is running  2) the password in DATABASE_URL is right  "
            "3) the database exists (create it in pgAdmin)  4) host/port are right.\n"
            "Fix DATABASE_URL (in backend/.env locally, or in the Render environment settings) and try again."
        ) from None
    with connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
