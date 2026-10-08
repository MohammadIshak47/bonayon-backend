import pandas as pd

from app.core.agronomy import MIN_DAYS_PER_MONTH


def monthly_table(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per (year, month) with enough valid days. Partial months are dropped so they cannot bias averages."""
    cols = ["year", "month", "valid_rain", "rain", "temp", "heat", "dry"]
    if frame.empty:
        return pd.DataFrame(columns=cols)
    g = frame.groupby(["year", "month"]).agg(
        valid_rain=("rainfall_mm", "count"), rain=("rainfall_mm", "sum"), temp=("temp_avg", "mean"),
        heat=("heatwave_day", "sum"), dry=("dry_spell", "any"),
    ).reset_index()
    return g[g["valid_rain"] >= MIN_DAYS_PER_MONTH].reset_index(drop=True)


def num(x: object, digits: int = 2) -> float | None:
    """NaN/None -> None, otherwise rounded float (JSON-safe)."""
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if v != v else round(v, digits)
