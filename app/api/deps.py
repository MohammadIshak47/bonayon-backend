import uuid
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ForbiddenError
from app.core.security import decode_token
from app.integrations.climate_provider import ClimateProvider
from app.integrations.factory import build_provider
from app.models import Role, User
from app.repositories import users as users_repo

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    sub = decode_token(token)
    try:
        user = users_repo.get(db, uuid.UUID(sub)) if sub else None
    except ValueError:
        user = None
    if user is None or not user.is_active:  # role/active are read from the DB every request, so deactivation is immediate
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise ForbiddenError("Administrator access required")
    return user


@lru_cache
def _provider() -> ClimateProvider:
    return build_provider()


def get_climate_provider() -> ClimateProvider:
    return _provider()
