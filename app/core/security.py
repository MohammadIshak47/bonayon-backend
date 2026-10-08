from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str:
    return _pwd.hash(p)


def verify_password(p: str, hashed: str) -> bool:
    return _pwd.verify(p, hashed)


def create_access_token(subject: str) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": exp}, s.JWT_SECRET, algorithm=s.JWT_ALGORITHM)


def decode_token(token: str) -> str | None:
    """Returns the subject (user id) or None if the token is invalid/expired."""
    s = get_settings()
    try:
        return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALGORITHM]).get("sub")
    except JWTError:
        return None
