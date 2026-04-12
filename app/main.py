"""
Аппликейшны entry point.
Router-уудыг холбож, middleware тохируулна.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.core.middleware import apply_rate_limit
from app.api.routes import entries, graph, websocket, demo

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
    # allow_origins=_settings.cors_origins_list,
    allow_origins= ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(entries.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(websocket.router)

# ── System ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def check_health():
    """Redis болон Supabase холболт шалгана."""
    from app.db.redis_client import get_redis_connection
    from app.db.supabase import get_anon_client

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
    logging.getLogger(__name__).info(
        f"🚀 Систем эхэллээ | env={_settings.app_env}"
        f" | model={_settings.llm_model}"
    )
