from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-driven config. Real values live in Render env / .env (gitignored). Security.md §5."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    user_token: str = ""
    agent_token: str = ""
    cors_origin: str = ""
    env: str = "dev"
    day_total: int = 84  # plan length; Day N/84 (PRD F9)


settings = Settings()
