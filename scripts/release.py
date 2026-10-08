"""Run on every deploy (Render build step), AFTER `alembic upgrade head`. Safe to run repeatedly.

1. Seeds the 64 districts and 8 crops (idempotent: existing rows are skipped).
2. Creates/promotes the first admin IF the ADMIN_EMAIL and ADMIN_PASSWORD environment variables are set.
   (Render's free plan has no shell, so this is how the first admin is created. Remove both variables afterwards.)
"""
import os

from app.core.db import SessionLocal
from scripts import create_admin, seed_crops, seed_districts


def main() -> None:
    with SessionLocal() as db:
        print(f"seed: districts +{seed_districts.seed(db)}, crops +{seed_crops.seed(db)}")
    email, password = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
    if email and password:
        create_admin.main(email, password, os.environ.get("ADMIN_NAME", "Administrator"))
    else:
        print("admin: ADMIN_EMAIL / ADMIN_PASSWORD not set, skipping")


if __name__ == "__main__":
    main()
