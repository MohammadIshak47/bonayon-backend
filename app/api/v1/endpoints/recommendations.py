from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_climate_provider, get_current_user
from app.core.db import get_db
from app.integrations.climate_provider import ClimateProvider
from app.models import Recommendation, RecommendationType, User
from app.repositories import recommendations as repo
from app.schemas.common import Page
from app.schemas.recommendation import (CropChoiceIn, DashboardOut, EstimateIn, EstimateOut, RecommendationOut, RotationPlanIn,
                                        RotationPlanOut, RotationSuggestIn, RotationSuggestOut, SeasonPlanIn)
from app.services import dashboard as dashboard_service
from app.services import input_estimator, recommendations as service, rotation as rotation_service
from sqlalchemy import select
from app.models import RotationPlan

router = APIRouter(tags=["Recommendations"])


@router.post("/recommendations/crop-choice", response_model=RecommendationOut, status_code=201, summary="Rank the top 5 crops (Engine 1)")
def crop_choice(body: CropChoiceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user), provider: ClimateProvider = Depends(get_climate_provider)) -> Recommendation:
    return service.crop_choice(db, user, provider, body)


@router.post("/recommendations/season-plan", response_model=RecommendationOut, status_code=201, summary="Season plan with planting window (Engine 3)")
def season_plan(body: SeasonPlanIn, db: Session = Depends(get_db), user: User = Depends(get_current_user), provider: ClimateProvider = Depends(get_climate_provider)) -> Recommendation:
    return service.season_plan_for(db, user, provider, body)


@router.get("/recommendations", response_model=Page[RecommendationOut], summary="Your recommendation history")
def history(type: RecommendationType | None = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items, total = repo.history(db, user, type, page, size)
    return Page[RecommendationOut](items=items, total=total, page=page, size=size)


@router.post("/rotation/suggest", response_model=RotationSuggestOut, tags=["Rotation & calculator"])
def rotation_suggest(body: RotationSuggestIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {"suggestions": rotation_service.suggest(db, body.season_1_crop_id)}


@router.post("/rotation/plans", response_model=RotationPlanOut, status_code=201, tags=["Rotation & calculator"])
def rotation_save(body: RotationPlanIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return rotation_service.save_plan(db, user, body.plot_id, body.season_1_crop_id, body.season_2_crop_id, body.note)


@router.get("/rotation/plans", response_model=list[RotationPlanOut], tags=["Rotation & calculator"])
def rotation_list(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(RotationPlan).where(RotationPlan.user_id == user.id).order_by(RotationPlan.created_at.desc())))


@router.post("/calculator/input-estimate", response_model=EstimateOut, tags=["Rotation & calculator"], summary="Seed estimate (Engine 5)")
def input_estimate(body: EstimateIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return input_estimator.estimate(db, body.crop_id, body.area_decimal)


@router.get("/dashboard", response_model=DashboardOut, tags=["Dashboard"])
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return dashboard_service.build(db, user)
