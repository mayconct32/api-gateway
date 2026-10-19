from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centraliza as configurações e credenciais da aplicação.

    Nenhum segredo é definido no código: os valores sensíveis são
    sempre lidos de variáveis de ambiente (ou arquivo .env), que não
    deve ser versionado. Use .env.example como referência.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "prod"] = "dev"
    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./dev.db"

    # Usado para assinar/verificar tokens JWT. Precisa ter ~32+ caracteres.
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: float = 30.0

    # Stripe
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None

    # Razorpay
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Carrega o arquivo .env uma única vez (singleton)."""
    return Settings()
