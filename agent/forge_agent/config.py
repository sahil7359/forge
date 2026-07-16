from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base: str = ""
    agent_token: str = ""
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b-instruct"
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:help.sahil.gob@gmail.com"
    ollama_timeout_s: int = 90


settings = AgentSettings()
