"""ENGINE 2: Risk calendar from daily flags. Thresholds live in app/core/agronomy.py."""
import pandas as pd

from app.core.agronomy import MONSOON_ONSET_RAIN_MM
from app.utils.monthly import num


def build_risk_calendar(table: pd.DataFrame) -> tuple[list[dict], int]:
    """Per month: avg heatwave days, dry-spell likelihood (% of years with a 7+ day dry run), monsoon onset flag."""
    months: list[dict] = []
    onset_done = False
    for m in range(1, 13):
        sub = table[table["month"] == m]
        if sub.empty:
            continue  # never invent a month we have no complete data for
        onset = False
        if not onset_done and sub["rain"].mean() >= MONSOON_ONSET_RAIN_MM:
            onset, onset_done = True, True
        months.append({
            "month": m,
            "heatwave_days": num(sub["heat"].mean(), 2) or 0.0,
            "dry_spell_likelihood": num(sub["dry"].mean() * 100, 1) or 0.0,
            "monsoon_onset": onset,
        })
    return months, int(table["year"].nunique()) if not table.empty else 0
