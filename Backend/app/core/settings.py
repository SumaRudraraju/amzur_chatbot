import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    LLM_MODEL: str = "gpt-4o"
    SUPABASE_URL: str = ""
    AMZUR_EMPLOYEE_DOMAIN: str = "amzur.com"
    ALLOWED_EMPLOYEE_DOMAINS: str = "amzur.com,stackyon.com"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    APP_ENV: str = "dev"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AUTH_COOKIE_NAME: str = "amzur_access_token"

    @property
    def cookie_secure(self) -> bool:
        return self.APP_ENV.lower() in {"prod", "production"}


settings = AppSettings()
