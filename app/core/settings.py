from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Аппликейшны бүх тохиргоог .env файлаас уншина.
    lru_cache ашиглан нэг удаа инициализ хийнэ.
    """

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM — Vertex
    llm_base_url: str = "https://aiplatform.googleapis.com/v1beta1/projects/mind-step/locations/us-central1/endpoints/openapi"
    llm_api_key: str
    llm_model: str = "google/gemini-2.5-flash"           # Seed / Analysis — хурдан, хямд
    llm_model_batch: str = "google/gemini-2.5-pro "          # Batch (human insight) — нарийн, чанартай
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_max_tokens_batch: int = 10000         # 5 insight × ~600 token

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Rate limiting
    rate_limit_per_minute: int = 3

    # Demo endpoint — өдөрт IP-р хэдэн удаа
    demo_daily_limit: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()