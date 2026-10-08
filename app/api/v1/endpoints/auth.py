from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories import users as users_repo
from app.schemas.user import RegisterIn, TokenOut, UserOut
from fastapi import HTTPException, status

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201, summary="Create a farmer account")
def register(body: RegisterIn, db: Session = Depends(get_db)) -> User:
    email = body.email.lower()
    if users_repo.get_by_email(db, email):
        raise ConflictError("Email already registered")
    return users_repo.create(db, name=body.name.strip(), email=email, phone=body.phone, password_hash=hash_password(body.password))


@router.post("/login", response_model=TokenOut, summary="OAuth2 password login (form: username=email, password)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenOut:
    user = users_repo.get_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)) -> User:
    return user
