from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.repositories import catalog as catalog_repo
from app.schemas.catalog import CropOut, DistrictOut

router = APIRouter(tags=["Reference"])


@router.get("/districts", response_model=list[DistrictOut], summary="All 64 districts (public)")
def districts(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=3600"  # reference data changes rarely
    return catalog_repo.list_districts(db)


@router.get("/crops", response_model=list[CropOut], summary="Active crop catalog")
def crops(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return catalog_repo.list_crops(db)


@router.get("/health", summary="Liveness check")
def health() -> dict:
    return {"status": "ok"}
