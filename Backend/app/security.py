from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import JWTError, jwt

from .core.settings import settings


class AuthTokenError(ValueError):
    pass


def create_access_token(user_id: str) -> tuple[str, dict[str, Any]]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    session_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "sid": session_id,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, payload


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthTokenError("Invalid or expired authentication token.") from exc

    if "user_id" not in payload or "iat" not in payload or "exp" not in payload:
        raise AuthTokenError("Invalid token payload.")
    return payload
