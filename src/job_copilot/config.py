from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://copilot:copilot@localhost:5432/copilot"

    # Routage de modèles : petit modèle pour le tri, gros pour la rédaction/vérification
    llm_fast_model: str = "anthropic/claude-haiku-5-5"
    llm_strong_model: str = "anthropic/claude-sonnet-5-5"
    eval_judge_model: str = "anthropic/claude-opus-5-5"

    embed_model: str = "ollama/bge-m3"
    embed_dim: int = 1024

    profile_path: str = "data/profile.yaml"
    prompt_version: str = "v1"
    shortlist_size: int = 30
    max_attempts: int = 3
    grounding_threshold: float = 0.0

    ft_client_id: str = ""
    ft_client_secret: str = ""
    ft_keywords: str = "ingénieur IA,machine learning,MLOps,data scientist"
    ft_departments: str = "33"
    rss_feeds: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    api_url: str = "http://localhost:8000"

    @property
    def keywords(self) -> list[str]:
        return [k.strip() for k in self.ft_keywords.split(",") if k.strip()]

    @property
    def departments(self) -> list[str]:
        return [d.strip() for d in self.ft_departments.split(",") if d.strip()]

    @property
    def feeds(self) -> list[str]:
        return [f.strip() for f in self.rss_feeds.split(",") if f.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
