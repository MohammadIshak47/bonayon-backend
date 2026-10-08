import uuid
from datetime import date

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import ClimateRecord

_BATCH = 2000  # 2000 rows x ~10 params stays under PostgreSQL's 65,535 bind-parameter limit


def existing_dates(db: Session, district_id: uuid.UUID, start: date, end: date) -> set[date]:
    rows = db.scalars(select(ClimateRecord.date).where(
        ClimateRecord.district_id == district_id, ClimateRecord.date.between(start, end)))
    return set(rows)


def insert_rows(db: Session, district_id: uuid.UUID, rows: list[dict]) -> None:
    for i in range(0, len(rows), _BATCH):
        chunk = [{**r, "district_id": district_id} for r in rows[i:i + _BATCH]]
        db.execute(pg_insert(ClimateRecord).values(chunk).on_conflict_do_nothing(index_elements=["district_id", "date"]))


def load_frame(db: Session, district_id: uuid.UUID, start: date, end: date) -> pd.DataFrame:
    cols = [ClimateRecord.date, ClimateRecord.temp_max, ClimateRecord.temp_avg, ClimateRecord.rainfall_mm,
            ClimateRecord.humidity, ClimateRecord.wind_speed, ClimateRecord.heatwave_day, ClimateRecord.dry_spell]
    rows = db.execute(select(*cols).where(ClimateRecord.district_id == district_id, ClimateRecord.date.between(start, end)).order_by(ClimateRecord.date)).all()
    frame = pd.DataFrame(rows, columns=["date", "temp_max", "temp_avg", "rainfall_mm", "humidity", "wind_speed", "heatwave_day", "dry_spell"])
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"])
        frame["year"] = frame["date"].dt.year
        frame["month"] = frame["date"].dt.month
        frame[["temp_max", "temp_avg", "rainfall_mm"]] = frame[["temp_max", "temp_avg", "rainfall_mm"]].astype("float64")
    return frame


def latest_fetch(db: Session, district_id: uuid.UUID, start: date, end: date):
    return db.scalar(select(func.max(ClimateRecord.fetched_at)).where(
        ClimateRecord.district_id == district_id, ClimateRecord.date.between(start, end)))
