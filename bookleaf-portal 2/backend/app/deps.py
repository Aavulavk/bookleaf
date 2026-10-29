"""Auth middleware as FastAPI dependencies: identity first, then role checks."""
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .core.errors import AppError
from .core.security import decode_token
from .db import get_db
from .models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise AppError(401, "NOT_AUTHENTICATED", "Missing bearer token.")
    try:
        user_id = int(decode_token(creds.credentials)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AppError(401, "INVALID_TOKEN", "Token is invalid or expired.")
    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "User no longer exists.")
    return user


def require_author(user: User = Depends(get_current_user)) -> User:
    # Role comes from the database, never from the token payload.
    if user.role != "author" or user.author is None:
        raise AppError(403, "FORBIDDEN", "Author access required.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(403, "FORBIDDEN", "Admin access required.")
    return user
