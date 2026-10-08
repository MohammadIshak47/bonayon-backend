import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import BadRequestError
from app.models import Farm, Plot, User
from app.repositories import catalog as catalog_repo
from app.repositories import farms as repo
from app.schemas.common import Page
from app.schemas.farm import FarmIn, FarmOut, FarmPatch, PlotIn, PlotOut, PlotPatch

router = APIRouter(tags=["Farms & plots"])


@router.post("/farms", response_model=FarmOut, status_code=201)
def create_farm(body: FarmIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Farm:
    catalog_repo.get_district(db, body.district_id)
    farm = Farm(user_id=user.id, **body.model_dump())
    db.add(farm)
    db.commit()
    return farm


@router.get("/farms", response_model=Page[FarmOut])
def list_farms(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items, total = repo.list_farms(db, user, page, size)
    return Page[FarmOut](items=items, total=total, page=page, size=size)


@router.get("/farms/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Farm:
    return repo.get_owned_farm(db, farm_id, user)


@router.patch("/farms/{farm_id}", response_model=FarmOut)
def patch_farm(farm_id: uuid.UUID, body: FarmPatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Farm:
    farm = repo.get_owned_farm(db, farm_id, user)
    data = body.model_dump(exclude_unset=True)
    if "district_id" in data:
        if data["district_id"] is None:
            raise BadRequestError("district_id cannot be null")
        catalog_repo.get_district(db, data["district_id"])
    for k, v in data.items():
        setattr(farm, k, v)
    db.commit()
    return farm


@router.delete("/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    db.delete(repo.get_owned_farm(db, farm_id, user))
    db.commit()


@router.post("/farms/{farm_id}/plots", response_model=PlotOut, status_code=201)
def create_plot(farm_id: uuid.UUID, body: PlotIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Plot:
    farm = repo.get_owned_farm(db, farm_id, user)
    if body.crop_id:
        catalog_repo.get_crop(db, body.crop_id)
    plot = Plot(farm_id=farm.id, **body.model_dump())
    db.add(plot)
    db.commit()
    return plot


@router.get("/farms/{farm_id}/plots", response_model=list[PlotOut])
def list_plots(farm_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return repo.list_plots(db, repo.get_owned_farm(db, farm_id, user))


@router.get("/plots/{plot_id}", response_model=PlotOut)
def get_plot(plot_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Plot:
    return repo.get_owned_plot(db, plot_id, user)


@router.patch("/plots/{plot_id}", response_model=PlotOut)
def patch_plot(plot_id: uuid.UUID, body: PlotPatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Plot:
    plot = repo.get_owned_plot(db, plot_id, user)
    data = body.model_dump(exclude_unset=True)
    if data.get("crop_id"):
        catalog_repo.get_crop(db, data["crop_id"])
    for k, v in data.items():
        setattr(plot, k, v)
    db.commit()
    return plot


@router.delete("/plots/{plot_id}", status_code=204)
def delete_plot(plot_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    db.delete(repo.get_owned_plot(db, plot_id, user))
    db.commit()
