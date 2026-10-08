"""Pre-download and cache climate for districts so the first user request is fast.
Run: python -m scripts.warm_climate Dhaka Rajshahi      (or with no names to warm all 64; slow with NASA)"""
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.integrations.factory import build_provider
from app.models import District
from app.services.climate_service import ensure_climate

if __name__ == "__main__":
    names = sys.argv[1:]
    provider = build_provider()
    with SessionLocal() as db:
        stmt = select(District).order_by(District.name_en)
        for d in db.scalars(stmt):
            if names and d.name_en not in names:
                continue
            b = ensure_climate(db, d, 20, provider)
            print(f"{d.name_en}: {len(b.frame)} days cached, sufficient={b.sufficient}, stale={b.stale}")
