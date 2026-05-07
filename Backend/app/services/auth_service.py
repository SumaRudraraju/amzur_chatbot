from passlib.context import CryptContext
import json
import secrets
import urllib.parse
import urllib.request

from .store_service import create_user, get_user_by_email, mark_last_login
from ..core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthError(ValueError):
    pass


def _validate_employee_email(email: str) -> str:
    normalized = email.strip().lower()
    domains = [d.strip().lower() for d in settings.ALLOWED_EMPLOYEE_DOMAINS.split(",") if d.strip()]
    if not domains:
        domains = [settings.AMZUR_EMPLOYEE_DOMAIN.strip().lower()]

    if "@" not in normalized:
        raise AuthError("Please provide a valid employee email address.")

    email_domain = normalized.rsplit("@", 1)[1]
    if email_domain not in domains:
        allowed_text = ", ".join(domains)
        raise AuthError(f"Only employee accounts from: {allowed_text}")
    return normalized


def signup_employee(email: str, password: str, full_name: str | None = None) -> dict:
    normalized_email = _validate_employee_email(email)
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")

    existing = get_user_by_email(normalized_email)
    if existing:
        raise AuthError("Account already exists. Please sign in.")

    password_hash = pwd_context.hash(password)
    return create_user(normalized_email, password_hash, full_name)


def signin_employee(email: str, password: str) -> dict:
    normalized_email = _validate_employee_email(email)
    user = get_user_by_email(normalized_email)
    if not user:
        raise AuthError("Invalid email or password.")

    if not pwd_context.verify(password, user["password_hash"]):
        raise AuthError("Invalid email or password.")

    mark_last_login(user["id"])
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name"),
    }


def get_google_login_url(state: str | None = None) -> str:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
        raise AuthError("Google login is not configured.")

    oauth_state = state or secrets.token_urlsafe(24)
    query = urllib.parse.urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": oauth_state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def _exchange_code_for_google_tokens(code: str) -> dict:
    token_url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_google_user(access_token: str) -> dict:
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    request = urllib.request.Request(
        userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def signin_with_google_code(code: str) -> dict:
    if not settings.GOOGLE_CLIENT_SECRET:
        raise AuthError("Google login is not configured.")

    try:
        tokens = _exchange_code_for_google_tokens(code)
        access_token = tokens.get("access_token")
        if not access_token:
            raise AuthError("Google token exchange failed.")

        profile = _fetch_google_user(access_token)
        email = _validate_employee_email(profile.get("email", ""))
        full_name = profile.get("name")

        user = get_user_by_email(email)
        if not user:
            random_hash = pwd_context.hash(secrets.token_urlsafe(32))
            created = create_user(email=email, password_hash=random_hash, full_name=full_name)
            user_id = created["id"]
        else:
            user_id = user["id"]

        mark_last_login(user_id)

        return {
            "id": user_id,
            "email": email,
            "full_name": full_name,
        }
    except AuthError:
        raise
    except Exception as exc:
        raise AuthError("Google authentication failed.") from exc
