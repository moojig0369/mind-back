"""
Worker эхлүүлэгч.
Ажиллуулах: python worker.py

Queue-ууд (priority дарааллаар):
  seed          — Seed Insight (хурдан, хамгийн өндөр)
  analysis      — Full analysis (Maslow/Plutchik/Hawkins)
  human_insight — Pattern-с монгол текст үүсгэх (LLM, бага priority)
  deep_insight  — Deep Insight (удаан, хамгийн бага priority)
"""

import logging
import sys
from dotenv import load_dotenv

load_dotenv()

from rq import Worker, Queue
from app.db.redis_client import get_redis_connection  # засвар: infrastructure → db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Queue-ийн дараалал = priority (эхний нь өндөр)
_QUEUES = ["seed", "analysis", "human_insight", "deep_insight"]

if __name__ == "__main__":
    conn = get_redis_connection()
    queues = [Queue(name, connection=conn) for name in _QUEUES]
    logging.getLogger(__name__).info(
        f"🔧 Worker эхэлж байна — queues: {_QUEUES}"
    )
    Worker(queues, connection=conn).work(with_scheduler=True)