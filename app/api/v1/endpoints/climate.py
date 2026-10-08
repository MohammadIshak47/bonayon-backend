import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_climate_provider, get_current_user
from app.core.agronomy import SEASON_MONTHS
from app.core.db import get_db
from app.core.errors import BadRequestError
from app.integrations.climate_provider import ClimateProvider
from app.models import User
from app.repositories import catalog as catalog_repo
from app.schemas.climate import AnomaliesOut, ProfileOut, RiskCalendarOut
from app.services.climate_service import build_profile, ensure_climate
from app.services.risk_calendar import build_risk_calendar
from app.utils.anomalies import yearly_anomalies
from app.utils.monthly import monthly_table

router = APIRouter(prefix="/climate", tags=["Climate"])


@router.get("/{district_id}/profile", response_model=ProfileOut, summary="Monthly climate averages (public; also serves the embeddable widget)")
def profile(district_id: uuid.UUID, years: int = Query(20, ge=1, le=30), db: Session = Depends(get_db), provider: ClimateProvider = Depends(get_climate_provider)) -> ProfileOut:
    district = catalog_repo.get_district(db, district_id)
    b = ensure_climate(db, district, years, provider)
    if not b.sufficient:
        return ProfileOut(district_id=district.id, years=years, months=[], stale=b.stale, source=b.source, insufficient_data=True)
    return ProfileOut(district_id=district.id, years=years, fetched_at=b.fetched_at, stale=b.stale, source=b.source, **build_profile(b))


@router.get("/{district_id}/risk-calendar", response_model=RiskCalendarOut, summary="Heatwave, dry-spell and monsoon-onset calendar")
def risk_calendar(district_id: uuid.UUID, season: str | None = None, db: Session = Depends(get_db), provider: ClimateProvider = Depends(get_climate_provider), _: User = Depends(get_current_user)) -> RiskCalendarOut:
    if season is not None and season not in SEASON_MONTHS:
        raise BadRequestError(f"Unknown season '{season}'. Choose one of: {', '.join(SEASON_MONTHS)}.")
    district = catalog_repo.get_district(db, district_id)
    b = ensure_climate(db, district, 20, provider)
    if not b.sufficient:
        return RiskCalendarOut(district_id=district.id, months=[], stale=b.stale, source=b.source, insufficient_data=True)
    months, basis = build_risk_calendar(monthly_table(b.frame))
    if season:
        months = [m for m in months if m["month"] in SEASON_MONTHS[season]]
    return RiskCalendarOut(district_id=district.id, months=months, basis_years=basis, fetched_at=b.fetched_at, stale=b.stale, source=b.source)


@router.get("/{district_id}/anomalies", response_model=AnomaliesOut, summary="Recent years vs the long-term average")
def anomalies(district_id: uuid.UUID, years: int = Query(5, ge=1, le=20), db: Session = Depends(get_db), provider: ClimateProvider = Depends(get_climate_provider), _: User = Depends(get_current_user)) -> AnomaliesOut:
    district = catalog_repo.get_district(db, district_id)
    b = ensure_climate(db, district, 20, provider)
    rows, baseline = yearly_anomalies(b.frame, years) if b.sufficient else ([], 0)
    return AnomaliesOut(district_id=district.id, years=rows, baseline_years=baseline or None, fetched_at=b.fetched_at, stale=b.stale, source=b.source, insufficient_data=not rows)
