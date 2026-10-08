import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.db import get_db
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models import Crop, Role, User
from app.repositories import audit
from app.repositories import catalog as catalog_repo
from app.repositories import users as users_repo
from app.schemas.catalog import CropIn, CropOut, CropPatch
from app.schemas.common import Page
from app.schemas.recommendation import AuditLogOut
from app.schemas.user import AdminUserUpdate, UserOut

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=Page[UserOut])
def list_users(query: str | None = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    items, total = users_repo.search(db, query, page, size)
    return Page[UserOut](items=items, total=total, page=page, size=size)


@router.patch("/users/{user_id}", response_model=UserOut, summary="Activate/deactivate a user (not yourself, not other admins)")
def update_user(user_id: uuid.UUID, body: AdminUserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> User:
    target = users_repo.get(db, user_id)
    if target is None:
        raise NotFoundError("User not found")
    if target.id == admin.id or target.role == Role.admin:
        raise ForbiddenError("You cannot change your own account or another administrator")
    target.is_active = body.is_active
    db.commit()
    audit.log(db, admin.id, "user.activate" if body.is_active else "user.deactivate", "user", target.id)
    return target


@router.get("/crops", response_model=list[CropOut], summary="All crops including inactive")
def admin_crops(db: Session = Depends(get_db)):
    return catalog_repo.list_crops(db, active_only=False)


@router.post("/crops", response_model=CropOut, status_code=201)
def create_crop(body: CropIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> Crop:
    crop = Crop(**body.model_dump(mode="json"))
    db.add(crop)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A crop with this English name already exists") from exc
    audit.log(db, admin.id, "crop.create", "crop", crop.id, {"name": crop.name_en})
    return crop


@router.patch("/crops/{crop_id}", response_model=CropOut)
def update_crop(crop_id: uuid.UUID, body: CropPatch, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> Crop:
    crop = catalog_repo.get_crop(db, crop_id)
    for k, v in body.model_dump(mode="json", exclude_unset=True).items():
        setattr(crop, k, v)
    if crop.rain_max_mm <= crop.rain_min_mm or crop.temp_max_c <= crop.temp_min_c:
        db.rollback()
        raise BadRequestError("max must be greater than min for rainfall and temperature ranges")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A crop with this English name already exists") from exc
    audit.log(db, admin.id, "crop.update", "crop", crop.id, {"fields": list(body.model_dump(exclude_unset=True))})
    return crop


@router.delete("/crops/{crop_id}", status_code=204)
def delete_crop(crop_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> None:
    crop = catalog_repo.get_crop(db, crop_id)
    db.delete(crop)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This crop is used by plots or rotation plans. Deactivate it instead of deleting.") from exc
    audit.log(db, admin.id, "crop.delete", "crop", crop_id, {"name": crop.name_en})


@router.get("/audit-logs", response_model=Page[AuditLogOut])
def audit_logs(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    items, total = audit.list_logs(db, page, size)
    return Page[AuditLogOut](items=items, total=total, page=page, size=size)
