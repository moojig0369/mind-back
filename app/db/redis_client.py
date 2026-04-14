"""
Redis холболт болон Queue factory.

Queue-ууд (priority дарааллаар):
  seed          — Seed Insight (хамгийн өндөр)
  analysis      — Full analysis (Maslow/Plutchik/Hawkins)
  human_insight — Pattern-с монгол insight үүсгэх
  deep_insight  — 10+ тэмдэглэлийн дараах гүн шинжилгээ
"""

from functools import lru_cache
import redis
from rq import Queue
from app.core.settings import get_settings

_settings = get_settings()


@lru_cache()
def get_redis_connection() -> redis.Redis:
    return redis.from_url(_settings.redis_url)


@lru_cache()
def get_seed_queue() -> Queue:
    """HIGH priority — Seed Insight хурдан дуусах ёстой."""
    return Queue("seed", connection=get_redis_connection())


@lru_cache()
def get_analysis_queue() -> Queue:
    """Normal priority — Maslow/Plutchik/Hawkins бүрэн шинжилгээ."""
    return Queue("analysis", connection=get_redis_connection())


@lru_cache()
def get_human_insight_queue() -> Queue:
    """Low priority — Pattern Engine дуусмагц human insight үүсгэнэ."""
    return Queue("human_insight", connection=get_redis_connection())


@lru_cache()
def get_deep_insight_queue() -> Queue:
    """Low priority — 10+ тэмдэглэлийн дараа."""
    return Queue("deep_insight", connection=get_redis_connection())