"""
Core configuration and shared utilities.
Production-ready settings with environment validation.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_name: str = "Journal Insights API"
    app_env: str = "development"
    app_version: str = "3.0.0"
    
    # Database (Supabase)
    supabase_url: str
    supabase_key: str
    supabase_anon_key: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # LLM (OpenAI or Vertex AI)
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    
    # CORS
    cors_origins: str = "*"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Background Jobs
    job_queue_name: str = "journal_jobs"
    job_max_retries: int = 3
    job_timeout_seconds: int = 300
    
    # Observability
    log_level: str = "INFO"
    enable_tracing: bool = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
