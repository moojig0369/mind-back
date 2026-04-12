"""
RQ Worker Jobs.

Урсгал:
  POST /api/entries
    → generate_seed_job  (seed queue, HIGH)
        └─ Seed done → run_analysis_job (analysis queue)
                           └─ Analysis done → WS

  10+ entries → process_deep_insight (deep_insight queue)
"""

import logging
from app.workers.job_helpers import run_async, publish, top_maslow_categories

_log = logging.getLogger(__name__)


# ── Job 1: Seed Insight ───────────────────────────────────────────────────────

def generate_seed_job(
    entry_id: str, user_id: str, entry_text: dict
) -> None:
    """
    Богино промптоор Seed Insight үүсгэж WS-оор буцаана.
    Дуусмагц run_analysis_job-г analysis queue-д нэмнэ.
    """
    from app.services.llm_service import get_llm_service
    from app.services.journal_service import JournalService
    from app.db.supabase import get_admin_client
    from app.db.redis_client import get_redis_connection, get_analysis_queue

    db = get_admin_client()
    journal = JournalService(db)
    redis = get_redis_connection()

    publish(redis, entry_id, "processing", "Seed Insight үүсгэж байна...")

    try:
        seed = run_async(
            get_llm_service().generate_seed_insight(**entry_text)
        )
        journal.save_seed_insight(entry_id, seed.model_dump())
        publish(redis, entry_id, "seed_done", payload=seed.model_dump())
        _log.info(f"Seed done: entry={entry_id}")

        get_analysis_queue().enqueue(
            "app.workers.jobs.run_analysis_job",
            entry_id=entry_id,
            user_id=user_id,
            entry_text=entry_text,
            job_timeout=120,
        )
    except Exception as exc:
        _log.error(f"Seed job алдаа: {exc}", exc_info=True)
        publish(redis, entry_id, "error", str(exc)[:120])
        raise


# ── Job 2: Full Analysis ──────────────────────────────────────────────────────

def run_analysis_job(
    entry_id: str, user_id: str, entry_text: dict
) -> None:
    """
    Maslow + Plutchik + Hawkins бүрэн шинжилгээ.
    Seed Insight дуусмагц ажиллана.
    """
    from app.services.llm_service import get_llm_service
    from app.services.journal_service import JournalService
    from app.db.supabase import get_admin_client
    from app.db.redis_client import get_redis_connection

    db = get_admin_client()
    journal = JournalService(db)
    redis = get_redis_connection()

    publish(redis, entry_id, "analyzing", "Гүн шинжилгээ хийж байна...")

    try:
        ewma = journal.get_user_ewma(user_id)
        result = run_async(
            get_llm_service().run_analysis(
                ewma_previous=ewma, **entry_text
            )
        )

        if result.hawkins.crisis_flag:
            _log.warning(f"CRISIS FLAG: user={user_id}, entry={entry_id}")
            publish(
                redis, entry_id, "crisis",
                "Мэргэжлийн тусламж авахыг зөвлөж байна",
            )

        print(f"Analysis result: {result}")

        journal.save_analysis(entry_id, result)
        journal.update_value_nodes(user_id, result, entry_id)
        journal.mark_analysis_processed(entry_id)

        publish(
            redis, entry_id, "analysis_done",
            payload={
                "hawkins_level": result.hawkins.level,
                "plutchik_primary": result.plutchik.primary,
                "plutchik_dyad": result.plutchik.dyad,
                "maslow_top": top_maslow_categories(result.maslow),
            },
        )
        _log.info(f"Analysis done: entry={entry_id}")

    except Exception as exc:
        _log.error(f"Analysis job алдаа: {exc}", exc_info=True)
        publish(redis, entry_id, "error", str(exc)[:120])
        raise


# ── Job 3: Deep Insight ───────────────────────────────────────────────────────

def process_deep_insight(user_id: str) -> None:
    """
    ValueGraph-д тулгуурлан Deep Insight үүсгэж
    хэрэглэгчид push notification илгээнэ.
    """
    from app.services.llm_service import get_llm_service
    from app.services.journal_service import JournalService
    from app.db.supabase import get_admin_client
    from app.db.redis_client import get_redis_connection

    db = get_admin_client()
    journal = JournalService(db)
    redis = get_redis_connection()

    count = journal.count_user_entries(user_id)
    summary = journal.build_graph_summary(user_id)
    insight = run_async(get_llm_service().generate_deep_insight(summary, count))

    db.table("deep_insights").insert(
        {
            "user_id": user_id,
            "insight_text": insight["insight_text"],
            "recommendations": insight["recommendations"],
        }
    ).execute()

    publish(
        redis,
        f"user:{user_id}:notifications",
        "deep_insight_ready",
        "Шинэ гүн шинжилгээ бэлэн боллоо",
    )
    _log.info(f"Deep Insight done: user={user_id}")
