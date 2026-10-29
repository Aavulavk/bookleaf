"""Central configuration. Every secret comes from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://bookleaf:bookleaf@localhost:5432/bookleaf"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 480
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    ai_timeout_seconds: float = 20.0
    cors_origins: str = "http://localhost:5173"

    @property
    def sqlalchemy_url(self) -> str:
        # Render/Railway hand out postgres:// URLs; SQLAlchemy needs a driver.
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url


settings = Settings()
