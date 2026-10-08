from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import BadRequestError
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut, summary="Update name/phone, or change password (current + new)")
def patch_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if body.new_password:
        if not verify_password(body.current_password or "", user.password_hash):
            raise BadRequestError("Current password is incorrect")
        user.password_hash = hash_password(body.new_password)
    if body.name is not None:
        user.name = body.name.strip()
    if "phone" in body.model_fields_set:
        user.phone = body.phone
    db.commit()
    return user
