from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://stock:stock@localhost:5432/tw_stock"
    redis_url: str = "redis://localhost:6379/0"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    market_data_provider: str = "mock"
    fugle_api_key: str = ""
    fubon_api_key: str = ""
    shioaji_api_key: str = ""
    shioaji_secret_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "alerts@example.com"
    line_channel_access_token: str = ""
    line_channel_secret: str = ""
    web_push_public_key: str = ""
    web_push_private_key: str = ""

    ecpay_merchant_id: str = ""
    ecpay_hash_key: str = ""
    ecpay_hash_iv: str = ""
    ecpay_return_url: str = "http://localhost:8000/api/billing/ecpay/return"
    ecpay_client_back_url: str = "http://localhost:3000/account"

    default_user_email: str = Field(default="demo@example.com")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
