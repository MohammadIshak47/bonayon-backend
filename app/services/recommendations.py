"""Orchestrates engines 1 and 3, persists the result exactly as shown, and writes an audit entry."""
from sqlalchemy.orm import Session

from app.core import agronomy as cfg
from app.core.errors import BadRequestError
from app.integrations.climate_provider import ClimateProvider
from app.models import Recommendation, RecommendationType, User
from app.repositories import audit
from app.repositories import catalog as catalog_repo
from app.repositories import farms as farms_repo
from app.repositories import recommendations as rec_repo
from app.schemas.recommendation import CropChoiceIn, SeasonPlanIn
from app.services import season_plan, suitability
from app.services.analysis import YEARS, analyze


def _basis(a, season: str, st: dict) -> list[str]:
    return [
        f"Based on {a.basis_years} years of {a.bundle.source} daily data for the district headquarters location.",
        f"Annual rainfall used: {st['annual_rain']:,.0f} mm. {season} average temperature used: {st['season_temp']:.1f} °C.",
        "Weights: " + ", ".join(f"{k} {v:.0%}" for k, v in cfg.WEIGHTS.items()) + ".",
        *cfg.LIMITATIONS,
    ]


def _check_season(season: str) -> None:
    if season not in cfg.SEASON_MONTHS:
        raise BadRequestError(f"Unknown season '{season}'. Choose one of: {', '.join(cfg.SEASON_MONTHS)}.")


def _meta(a) -> dict:
    return {"source": a.bundle.source, "data_fetched_at": a.bundle.fetched_at.isoformat() if a.bundle.fetched_at else None, "stale": a.bundle.stale, "years": YEARS}


def crop_choice(db: Session, user: User, provider: ClimateProvider, data: CropChoiceIn) -> Recommendation:
    _check_season(data.season)
    district = catalog_repo.get_district(db, data.district_id)
    a = analyze(db, district, provider)
    results = suitability.score_crops(catalog_repo.list_crops(db), a, data.soil_type.value, data.season)
    st = suitability.season_stats(a, data.season)
    rec = rec_repo.add(
        db, user_id=user.id, plot_id=None, type=RecommendationType.crop_choice, district_id=district.id, season=data.season,
        payload={"results": results, "limitations": cfg.LIMITATIONS, **_meta(a)}, explanations=_basis(a, data.season, st),
        advisory_text=None, disclaimer=cfg.DISCLAIMER,
    )
    audit.log(db, user.id, "recommendation.crop_choice", "recommendation", rec.id, {"district": district.name_en, "season": data.season})
    return rec


def season_plan_for(db: Session, user: User, provider: ClimateProvider, data: SeasonPlanIn) -> Recommendation:
    plot_id = None
    if data.plot_id:
        plot = farms_repo.get_owned_plot(db, data.plot_id, user)  # 403 for someone else's plot
        farm = farms_repo.get_owned_farm(db, plot.farm_id, user)
        if not plot.season:
            raise BadRequestError("This plot has no season set. Add a season to the plot or enter the details manually.")
        district_id, soil, season, plot_id = farm.district_id, plot.soil_type.value, plot.season, plot.id
    else:
        district_id, soil, season = data.district_id, data.soil_type.value, data.season  # type: ignore[union-attr,assignment]
    _check_season(season)  # type: ignore[arg-type]
    district = catalog_repo.get_district(db, district_id)  # type: ignore[arg-type]
    a = analyze(db, district, provider)
    ranked = suitability.score_crops(catalog_repo.list_crops(db), a, soil, season)  # type: ignore[arg-type]
    if not ranked:
        raise BadRequestError("The crop catalog has no active crops to score.")
    best = ranked[0]
    window = season_plan.planting_window(a, season)  # type: ignore[arg-type]
    st = suitability.season_stats(a, season)  # type: ignore[arg-type]
    text = season_plan.advisory_text(district.name_en, best, season, soil, window, a.basis_years)  # type: ignore[arg-type]
    rec = rec_repo.add(
        db, user_id=user.id, plot_id=plot_id, type=RecommendationType.season_plan, district_id=district.id, season=season,  # type: ignore[arg-type]
        payload={"crop": best, "planting_window": {k: window[k] for k in ("start", "end", "note")}, "risk_warnings": window["risk_warnings"],
                 "alternatives": ranked[1:3], "limitations": cfg.LIMITATIONS, **_meta(a)},
        explanations=[*best["explanations"], *_basis(a, season, st)],  # type: ignore[arg-type]
        advisory_text=text, disclaimer=cfg.DISCLAIMER,
    )
    audit.log(db, user.id, "recommendation.season_plan", "recommendation", rec.id, {"district": district.name_en, "season": season})
    return rec
