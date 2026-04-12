"""
Core configuration and shared utilities.
Production-ready settings with environment validation.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_name: str = "Journal Insights API"
    app_env: str = "development"
    app_version: str = "3.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # Database (Supabase)
    supabase_url: str

    supabase_service_role_key: str
    supabase_anon_key: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # LLM (OpenAI or Vertex AI)
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    
    # CORS
    cors_origins: str = "*"
    
    # Rate Limiting
    rate_limit_per_minute: Optional[int] = None  # Alias for rate_limit_requests
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Background Jobs (RQ)
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
    
    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL from Supabase credentials."""
        # Use service role key if available, otherwise fallback to supabase_key
        db_password = self.supabase_service_role_key
        
        if "supabase.co" in self.supabase_url:
            # Extract project ID from Supabase URL
            db_host = self.supabase_url.replace("https://", "").replace(".supabase.co", "")
            # Use service role key for database password
            return (
                f"postgresql+asyncpg://postgres:{db_password}@"
                f"{db_host}.pooler.supabase.com:6543/postgres"
            )
        # Fallback for direct PostgreSQL URLs
        return self.supabase_url.replace("postgres://", "postgresql+asyncpg://")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
