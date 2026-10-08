"""Fetch-with-cache for daily climate, plus the monthly profile. Only missing days are requested."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.core.agronomy import DRY_DAY_MM, DRY_SPELL_MIN_DAYS, HEATWAVE_TEMP_C, MIN_RECORDS_FOR_PROFILE
from app.core.config import get_settings
from app.integrations.climate_provider import ClimateProvider, DailyClimate, ProviderError
from app.models import District
from app.repositories import climate as repo
from app.utils.monthly import monthly_table, num

MERGE_GAP_DAYS = 30  # nearby gaps are fetched in one request instead of many


@dataclass
class ClimateBundle:
    frame: pd.DataFrame
    fetched_at: datetime | None
    stale: bool
    source: str
    start: date
    end: date
    sufficient: bool


def flag_days(days: list[DailyClimate]) -> list[dict]:
    """Rows ready to insert, with heatwave_day and dry_spell computed. A dry spell is a run of
    >= DRY_SPELL_MIN_DAYS consecutive days with rainfall < DRY_DAY_MM; every day in the run is flagged."""
    days = sorted(days, key=lambda d: d.date)
    rows = [{
        "date": d.date, "temp_max": d.temp_max, "temp_avg": d.temp_avg, "rainfall_mm": d.rainfall_mm,
        "humidity": d.humidity, "wind_speed": d.wind_speed,
        "heatwave_day": d.temp_max is not None and d.temp_max >= HEATWAVE_TEMP_C, "dry_spell": False,
    } for d in days]
    run_start: int | None = None
    for i, d in enumerate(days + [None]):  # type: ignore[list-item]
        dry = d is not None and d.rainfall_mm is not None and d.rainfall_mm < DRY_DAY_MM
        consecutive = dry and run_start is not None and d is not None and (d.date - days[i - 1].date).days == 1
        if dry and (run_start is None or not consecutive):
            if run_start is not None and i - run_start >= DRY_SPELL_MIN_DAYS:
                for j in range(run_start, i):
                    rows[j]["dry_spell"] = True
            run_start = i
        elif not dry:
            if run_start is not None and i - run_start >= DRY_SPELL_MIN_DAYS:
                for j in range(run_start, i):
                    rows[j]["dry_spell"] = True
            run_start = None
    return rows


def missing_ranges(start: date, end: date, existing: set[date]) -> list[tuple[date, date]]:
    missing = [start + timedelta(days=i) for i in range((end - start).days + 1) if start + timedelta(days=i) not in existing]
    ranges: list[tuple[date, date]] = []
    for d in missing:
        if ranges and (d - ranges[-1][1]).days <= MERGE_GAP_DAYS:
            ranges[-1] = (ranges[-1][0], d)
        else:
            ranges.append((d, d))
    return ranges


def ensure_climate(db: Session, district: District, years: int, provider: ClimateProvider, today: date | None = None) -> ClimateBundle:
    end = (today or date.today()) - timedelta(days=get_settings().CLIMATE_END_LAG_DAYS)
    start = end - timedelta(days=365 * years)
    stale = False
    ranges = missing_ranges(start, end, repo.existing_dates(db, district.id, start, end))
    if ranges:
        try:
            for s, e in ranges:
                repo.insert_rows(db, district.id, flag_days(provider.fetch_daily(district.lat, district.lon, s, e)))
            db.commit()
        except ProviderError:
            db.rollback()
            stale = True  # fall back to whatever is cached; the response says so
    frame = repo.load_frame(db, district.id, start, end)
    needed = min(MIN_RECORDS_FOR_PROFILE, int(0.8 * years * 365))
    return ClimateBundle(frame, repo.latest_fetch(db, district.id, start, end), stale, provider.name, start, end, len(frame) >= needed)


def build_profile(bundle: ClimateBundle) -> dict:
    t = monthly_table(bundle.frame)
    months = []
    for m in range(1, 13):
        sub = t[t["month"] == m]
        if sub.empty:
            continue
        months.append({"month": m, "temp_avg": num(sub["temp"].mean(), 1), "rainfall_mm": num(sub["rain"].mean(), 1)})
    rain = [x["rainfall_mm"] for x in months]
    temp = [x["temp_avg"] for x in months if x["temp_avg"] is not None]
    return {
        "months": months,
        "annual_rainfall_mm": num(sum(rain), 1) if len(months) == 12 and None not in rain else None,
        "mean_temp_c": num(sum(temp) / len(temp), 1) if temp else None,
        "data_span": {"start": bundle.start, "end": bundle.end} if not bundle.frame.empty else None,
    }
