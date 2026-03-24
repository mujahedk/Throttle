from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    throttle_env: str = Field(default="dev", alias="THROTTLE_ENV")
    throttle_api_keys: str = Field(default="dev_key_123", alias="THROTTLE_API_KEYS")
    throttle_require_api_key: bool = Field(default=True, alias="THROTTLE_REQUIRE_API_KEY")
    throttle_redis_url: str = Field(default="redis://localhost:6379/0", alias="THROTTLE_REDIS_URL")
    throttle_rate_limit: int = Field(default=10, alias="THROTTLE_RATE_LIMIT")
    throttle_window_seconds: int = Field(default=60, alias="THROTTLE_WINDOW_SECONDS")

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.throttle_api_keys.split(",") if k.strip()}


settings = Settings()
