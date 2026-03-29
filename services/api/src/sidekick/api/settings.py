"""Runtime settings for the API service."""

from functools import lru_cache
from os import getenv


class Settings:
    """Configuration loaded from environment variables."""

    database_url: str
    cognito_region: str
    cognito_user_pool_id: str
    cognito_issuer: str
    cognito_audience: str
    api_key_pepper: str
    cors_allowed_origins: list[str]

    def __init__(self) -> None:
        self.database_url = getenv("DATABASE_URL", "")
        self.cognito_region = getenv("COGNITO_REGION", "")
        self.cognito_user_pool_id = getenv("COGNITO_USER_POOL_ID", "")
        self.cognito_issuer = getenv("COGNITO_ISSUER", "")
        self.cognito_audience = getenv("COGNITO_AUDIENCE", "")
        self.api_key_pepper = getenv("API_KEY_PEPPER", "")
        raw_cors_origins = getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,"
            "http://localhost:3000,http://127.0.0.1:3000",
        )
        self.cors_allowed_origins = [
            origin.strip() for origin in raw_cors_origins.split(",") if origin.strip()
        ]

    @property
    def jwks_url(self) -> str:
        """Return the Cognito JWKS URL."""
        if self.cognito_region and self.cognito_user_pool_id:
            return (
                f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
                f"{self.cognito_user_pool_id}/.well-known/jwks.json"
            )
        if self.cognito_issuer:
            return f"{self.cognito_issuer.rstrip('/')}/.well-known/jwks.json"
        return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()
