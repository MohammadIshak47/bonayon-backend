"""Seed districts and crops. Run: python -m scripts.seed_all"""
from app.core.db import SessionLocal
from scripts import seed_crops, seed_districts

if __name__ == "__main__":
    with SessionLocal() as db:
        print(f"districts: +{seed_districts.seed(db)}, crops: +{seed_crops.seed(db)}")
