from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-driven config. Real values live in Render env / .env (gitignored). Security.md §5."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    user_token: str = ""
    agent_token: str = ""
    cors_origin: str = ""
    env: str = "dev"


settings = Settings()
