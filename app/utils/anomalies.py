import pandas as pd

from app.core.agronomy import MIN_DAYS_PER_YEAR
from app.utils.monthly import num


def yearly_anomalies(frame: pd.DataFrame, recent_years: int) -> tuple[list[dict], int]:
    """Per-year mean temperature and rainfall total vs the average of ALL complete years in the window.
    (The baseline includes the recent years themselves; the caption in the UI says so.)"""
    if frame.empty:
        return [], 0
    y = frame.groupby("year").agg(days=("rainfall_mm", "count"), rain=("rainfall_mm", "sum"), temp=("temp_avg", "mean")).reset_index()
    y = y[y["days"] >= MIN_DAYS_PER_YEAR].reset_index(drop=True)
    if y.empty:
        return [], 0
    base_rain, base_temp = y["rain"].mean(), y["temp"].mean()
    out = []
    for r in y.tail(recent_years).itertuples():
        out.append({
            "year": int(r.year),
            "temp_anomaly_c": num(r.temp - base_temp),
            "rainfall_anomaly_pct": num((r.rain - base_rain) / base_rain * 100) if base_rain else None,
        })
    return out, len(y)
