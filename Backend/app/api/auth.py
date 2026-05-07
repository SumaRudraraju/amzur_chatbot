import json

from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ..dependencies.auth import get_current_user
from ..schemas.chat_schema import AuthRequest, AuthStatusResponse, ErrorResponse, UserResponse
from ..core.settings import settings
from ..security import create_access_token, decode_access_token
from ..services.auth_service import (
    AuthError,
    get_google_login_url,
    signin_employee,
    signin_with_google_code,
    signup_employee,
)
from ..services.store_service import create_auth_session, revoke_auth_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


def format_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post("/signup", response_model=UserResponse, responses={400: {"model": ErrorResponse}})
async def signup(payload: AuthRequest):
    try:
        user = signup_employee(payload.email, payload.password, payload.full_name)
        response = JSONResponse(
            status_code=200,
            content=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            full_name=user.get("full_name"),
            ).model_dump(),
        )
        token, token_payload = create_access_token(str(user["id"]))
        create_auth_session(str(token_payload["sid"]), str(user["id"]), int(token_payload["exp"]))
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        return response
    except AuthError as exc:
        return format_error(400, "auth_error", str(exc))


@router.post("/signin", response_model=UserResponse, responses={400: {"model": ErrorResponse}})
async def signin(payload: AuthRequest):
    try:
        user = signin_employee(payload.email, payload.password)
        response = JSONResponse(
            status_code=200,
            content=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            full_name=user.get("full_name"),
            ).model_dump(),
        )
        token, token_payload = create_access_token(str(user["id"]))
        create_auth_session(str(token_payload["sid"]), str(user["id"]), int(token_payload["exp"]))
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        return response
    except AuthError as exc:
        return format_error(400, "auth_error", str(exc))


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    auth_cookie: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME),
):
    del current_user
    response = JSONResponse(status_code=200, content={"success": True})
    if auth_cookie:
        try:
            payload = decode_access_token(auth_cookie)
            session_id = payload.get("sid")
            if session_id:
                revoke_auth_session(str(session_id))
        except Exception:
            # Always clear cookie even when token parsing fails.
            pass
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=AuthStatusResponse, responses={401: {"model": ErrorResponse}})
async def me(current_user: dict = Depends(get_current_user)):
    return AuthStatusResponse(
        user=UserResponse(
            id=str(current_user["id"]),
            email=current_user["email"],
            full_name=current_user.get("full_name"),
        )
    )


@router.get("/google/login")
async def google_login():
    try:
        url = get_google_login_url()
        return RedirectResponse(url=url)
    except AuthError as exc:
        return format_error(400, "auth_error", str(exc))


@router.get("/google/callback")
async def google_callback(code: str | None = None, error: str | None = None):
    if error:
        html = (
            "<html><body><script>"
            f"window.opener && window.opener.postMessage({json.dumps({'type': 'amzur_google_auth_error', 'error': 'Google login failed.'})}, {json.dumps(settings.FRONTEND_ORIGIN)});"
            "window.close();"
            "</script></body></html>"
        )
        return HTMLResponse(content=html, status_code=400)

    if not code:
        return format_error(400, "auth_error", "Missing authorization code.")

    try:
        user = signin_with_google_code(code)
        token, token_payload = create_access_token(str(user["id"]))
        create_auth_session(str(token_payload["sid"]), str(user["id"]), int(token_payload["exp"]))
        message = {
            "type": "amzur_google_auth_success",
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user.get("full_name"),
            },
        }
        html = (
            "<html><body><script>"
            f"window.opener && window.opener.postMessage({json.dumps(message)}, {json.dumps(settings.FRONTEND_ORIGIN)});"
            "window.close();"
            "</script></body></html>"
        )
        response = HTMLResponse(content=html)
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        return response
    except AuthError as exc:
        message = {"type": "amzur_google_auth_error", "error": str(exc)}
        html = (
            "<html><body><script>"
            f"window.opener && window.opener.postMessage({json.dumps(message)}, {json.dumps(settings.FRONTEND_ORIGIN)});"
            "window.close();"
            "</script></body></html>"
        )
        return HTMLResponse(content=html, status_code=400)
