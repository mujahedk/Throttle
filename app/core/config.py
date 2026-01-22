from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # This tells pydantic-settings to load from .env automatically.
    # extra="ignore" means: if there are other env vars present, don't error.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Each field below becomes a setting.
    # alias="THROTTLE_ENV" means read from that env var name.
    throttle_env: str = Field(default="dev", alias="THROTTLE_ENV")

    # We store API keys as ONE string in env vars, then parse it later.
    throttle_api_keys: str = Field(
        default="dev_key_123", alias="THROTTLE_API_KEYS")

    # This is a boolean. pydantic converts "true"/"false" -> True/False.
    throttle_require_api_key: bool = Field(
        default=True, alias="THROTTLE_REQUIRE_API_KEY")

    throttle_redis_url: str = Field(
        default="redis://localhost:6379/0", alias="THROTTLE_REDIS_URL")
    throttle_rate_limit: int = Field(default=10, alias="THROTTLE_RATE_LIMIT")
    throttle_window_seconds: int = Field(
        default=60, alias="THROTTLE_WINDOW_SECONDS")

    @property
    def api_key_set(self) -> set[str]:
        """
            Convert the comma-separated API key string into a Python set.

            Why a set?
            - Fast membership checks: O(1) average case
            - avoids duplicates automatically
            """
        return {k.strip() for k in self.throttle_api_keys.split(",") if k.strip()}


settings = Settings()
