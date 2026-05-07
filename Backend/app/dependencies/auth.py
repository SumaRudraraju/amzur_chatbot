from fastapi import Cookie, HTTPException, status

from ..core.settings import settings
from ..security import AuthTokenError, decode_access_token
from ..services.store_service import get_user_by_id, is_session_active


def get_current_user(auth_cookie: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME)) -> dict:
    if not auth_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(auth_cookie)
    except AuthTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    session_id = payload.get("sid")
    if not session_id or not is_session_active(session_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired")

    user = get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
