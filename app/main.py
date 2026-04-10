"""
Аппликейшны entry point.
Router-уудыг холбож, middleware тохируулна.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.core.middleware import apply_rate_limit
from app.api.v1.journal_routes import router as journal_router
from app.api.v1.graph_routes import router as graph_router
from app.infrastructure.database import init_database, db
from app.infrastructure.redis_client import init_redis
from app.infrastructure.supabase_client import init_supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

_settings = get_settings()

app = FastAPI(
    title="Тэмдэглэлийн системийн API",
    version="1.0.0",
    docs_url="/docs" if _settings.app_env == "development" else None,
    redoc_url=None,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.middleware("http")(apply_rate_limit)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(journal_router, prefix="/api/v1", tags=["Journal"])
app.include_router(graph_router, prefix="/api/v1", tags=["Graph"])

# ── System ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def check_health():
    """Redis болон Supabase холболт шалгана."""
    from app.infrastructure.redis_client import get_redis_connection
    from app.infrastructure.supabase_client import get_anon_client

    result = {"api": "ok", "redis": "unknown", "supabase": "unknown"}

    try:
        get_redis_connection().ping()
        result["redis"] = "ok"
    except Exception as exc:
        result["redis"] = f"error: {exc}"

    try:
        get_anon_client().table("plans").select("id").limit(1).execute()
        result["supabase"] = "ok"
    except Exception as exc:
        result["supabase"] = f"error: {exc}"

    return result


@app.on_event("startup")
async def on_startup():
    """Initialize all infrastructure connections on startup."""
    logger = logging.getLogger(__name__)
    logger.info(
        f"🚀 Систем эхэллээ | env={_settings.app_env}"
        f" | model={_settings.llm_model}"
    )
    
    # Initialize database with properly constructed URL
    try:
        init_database(_settings.database_url)
        logger.info("✅ Database initialized")
    except Exception as exc:
        logger.error(f"❌ Database initialization failed: {exc}")
    
    # Initialize Redis
    try:
        if _settings.redis_url:
            init_redis(_settings.redis_url)
            logger.info("✅ Redis initialized")
    except Exception as exc:
        logger.error(f"❌ Redis initialization failed: {exc}")
    
    # Initialize Supabase
    try:
        init_supabase(
            _settings.supabase_url,
            _settings.supabase_key,
            _settings.supabase_anon_key
        )
        logger.info("✅ Supabase initialized")
    except Exception as exc:
        logger.error(f"❌ Supabase initialization failed: {exc}")


@app.on_event("shutdown")
async def on_shutdown():
    """Cleanup connections on shutdown."""
    await db.close()
    logging.getLogger(__name__).info("👋 System shutdown complete")
