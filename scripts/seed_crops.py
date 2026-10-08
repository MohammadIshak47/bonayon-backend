"""Seed 8 crops. Idempotent (matched by name_en). Run: python -m scripts.seed_crops

EVERY NUMBER BELOW IS A PROTOTYPE ASSUMPTION, "FAO-informed" in spirit but NOT copied from a specific FAO table and
NOT validated by an agronomist. Rainfall ranges are compared against ANNUAL rainfall and temperature ranges against the
growing season's average temperature (see app/services/suitability.py), so they are coarse by design.
Rotation lists and seed rates are likewise assumptions. Review with an agriculture expert before real use.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Crop, WaterSensitivity

H = WaterSensitivity.high
M = WaterSensitivity.medium
L = WaterSensitivity.low

# name_en: (name_bn, seasons, rain_min, rain_max, temp_min, temp_max, soils, water, seed_kg_per_decimal, npk_note, rotation_after names)
CROPS = {
    "Boro Rice": ("বোরো ধান", ["Rabi"], 1200, 2200, 20, 35, ["clay", "clay_loam", "silt_loam"], H, 0.30, "Assumption: split nitrogen doses; confirm rates locally.", ["Mustard"]),
    "Aman Rice": ("আমন ধান", ["Kharif"], 1300, 2500, 22, 35, ["clay", "clay_loam", "silt_loam"], H, 0.30, "Assumption: split nitrogen doses; confirm rates locally.", ["Wheat", "Mustard", "Potato"]),
    "Wheat": ("গম", ["Rabi"], 800, 1800, 10, 25, ["clay_loam", "silt_loam", "sandy_loam"], M, 0.50, "Assumption: basal NPK plus top-dressed nitrogen; confirm locally.", ["Aman Rice", "Maize"]),
    "Maize": ("ভুট্টা", ["Rabi", "Kharif"], 600, 2000, 18, 32, ["clay_loam", "sandy_loam", "silt_loam"], M, 0.08, "Assumption: high nitrogen demand; confirm locally.", ["Mustard", "Potato"]),
    "Potato": ("আলু", ["Rabi"], 800, 1800, 10, 25, ["sandy_loam", "silt_loam", "clay_loam"], M, 8.00, "Assumption: high potash demand; confirm locally.", ["Aman Rice"]),
    "Tomato": ("টমেটো", ["Rabi"], 800, 2000, 15, 30, ["sandy_loam", "silt_loam", "clay_loam"], M, 0.002, "Assumption: balanced NPK with calcium; confirm locally.", ["Aman Rice"]),
    "Eggplant": ("বেগুন", ["Kharif", "Rabi"], 1000, 2500, 20, 32, ["silt_loam", "clay_loam", "sandy_loam"], M, 0.002, "Assumption: regular nitrogen and potash; confirm locally.", ["Wheat", "Mustard"]),
    "Mustard": ("সরিষা", ["Rabi"], 500, 1600, 10, 25, ["sandy_loam", "silt_loam", "clay_loam"], L, 0.025, "Assumption: sulphur helps oil content; confirm locally.", ["Aman Rice", "Maize"]),
}


def seed(db: Session) -> int:
    existing = {c.name_en: c for c in db.scalars(select(Crop))}
    created = 0
    for name, (bn, seasons, rmin, rmax, tmin, tmax, soils, water, seed_kg, npk, _) in CROPS.items():
        if name in existing:
            continue
        db.add(Crop(name_en=name, name_bn=bn, seasons=seasons, rain_min_mm=rmin, rain_max_mm=rmax, temp_min_c=tmin, temp_max_c=tmax,
                    suitable_soils=soils, water_sensitivity=water, rotation_after=[], seed_kg_per_decimal=seed_kg, npk_note=npk, is_active=True))
        created += 1
    db.commit()
    by_name = {c.name_en: c for c in db.scalars(select(Crop))}
    for name, spec in CROPS.items():  # second pass: rotation_after stores crop ids, which exist only after insert
        crop = by_name[name]
        if not crop.rotation_after:
            crop.rotation_after = [str(by_name[n].id) for n in spec[-1]]
    db.commit()
    return created


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Inserted {seed(session)} crops")
