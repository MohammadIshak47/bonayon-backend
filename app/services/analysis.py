"""Shared climate analysis for the engines: monthly means + risk calendar, or an honest INSUFFICIENT_DATA."""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import InsufficientDataError
from app.integrations.climate_provider import ClimateProvider
from app.models import District
from app.services.climate_service import ClimateBundle, ensure_climate
from app.services.risk_calendar import build_risk_calendar
from app.utils.monthly import monthly_table

YEARS = 20


@dataclass
class Analysis:
    bundle: ClimateBundle
    monthly: dict[int, dict[str, float | None]]   # month -> {"temp":..., "rain":...}
    risk: dict[int, dict]                         # month -> risk row
    basis_years: int


def analyze(db: Session, district: District, provider: ClimateProvider) -> Analysis:
    bundle = ensure_climate(db, district, YEARS, provider)
    if not bundle.sufficient:
        raise InsufficientDataError(f"not enough climate data for {district.name_en} right now.")
    t = monthly_table(bundle.frame)
    monthly = {m: {"temp": float(s["temp"].mean()), "rain": float(s["rain"].mean())} for m in range(1, 13) if not (s := t[t["month"] == m]).empty}
    if len(monthly) < 12:
        raise InsufficientDataError(f"climate history for {district.name_en} does not cover all 12 months yet.")
    risk_rows, basis = build_risk_calendar(t)
    return Analysis(bundle, monthly, {r["month"]: r for r in risk_rows}, basis)
