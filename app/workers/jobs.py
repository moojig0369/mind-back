"""
RQ Worker Jobs.

Урсгал:
  POST /api/entries
    → generate_seed_job      (seed queue, HIGH)
        └─ run_analysis_job  (analysis queue)
               └─ 1–4. LLM + graph
               └─ 5. PatternEngine.run()
               └─ 6. Store detected_patterns
               └─ 7. generate_human_insight_job  (human_insight queue)
                        └─ LLM → human_insights хадгална
                        └─ WS: human_insight_ready

  10+ entries → process_deep_insight (deep_insight queue)

АНХААРУУЛГА:
  enqueue() дотор функцийг string-ээр биш, шууд reference-ээр дамжуулна.
  RQ 1.16-д "app.workers.jobs.func" гэсэн string import механизм
  app.workers → .jobs гэж буруу задлах bug байдаг.
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

        # Function reference ашиглана — string биш (RQ 1.16 bug тойрч гарна)
        get_analysis_queue().enqueue(
            run_analysis_job,
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

    Дараалал:
      1–3. LLM шинжилгээ
      4.   Graph шинэчлэлт
      5.   PatternEngine.run()
      6.   detected_patterns хадгалагдана (engine дотор)
      7.   generate_human_insight_job queue-д нэмнэ
    """
    from app.services.llm_service import get_llm_service
    from app.services.journal_service import JournalService
    # app/workers/pattern.py дотор PatternEngine байна (app/services/patttern_engine.py биш)
    from app.workers.pattern import PatternEngine
    from app.db.supabase import get_admin_client
    from app.db.redis_client import get_redis_connection

    db = get_admin_client()
    journal = JournalService(db)
    redis = get_redis_connection()

    publish(redis, entry_id, "analyzing", "Гүн шинжилгээ хийж байна...")

    try:
        # ── 1–3. LLM шинжилгээ ───────────────────────────────────────────────
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

        # ── 4. Graph шинэчлэлт ───────────────────────────────────────────────
        journal.save_analysis(entry_id, result)
        journal.update_value_nodes(user_id, result, entry_id)
        journal.mark_analysis_processed(entry_id)
        _log.info(f"Analysis + graph done: entry={entry_id}")

        # ── 5–6. Pattern Engine ───────────────────────────────────────────────
        run_id = _start_pattern_run(db, user_id)
        engine = PatternEngine(db)
        detected = engine.run(user_id=user_id, run_id=run_id)
        _log.info(
            f"Pattern Engine done: user={user_id}, "
            f"detected={len(detected)}, run_id={run_id}"
        )

        # ── 7. Human Insight queue-д нэмнэ ───────────────────────────────────
        if detected:
            from app.db.redis_client import get_human_insight_queue
            # Function reference ашиглана — string биш
            get_human_insight_queue().enqueue(
                generate_human_insight_job,
                user_id=user_id,
                run_id=run_id,
                entry_id=entry_id,
                job_timeout=60,
            )

        # ── WS мэдэгдэл ──────────────────────────────────────────────────────
        publish(
            redis, entry_id, "analysis_done",
            payload={
                "hawkins_level":    result.hawkins.level,
                "plutchik_primary": result.plutchik.primary,
                "plutchik_dyad":    result.plutchik.dyad,
                "maslow_top":       top_maslow_categories(result.maslow),
                "patterns_count":   len(detected),
                "run_id":           run_id,
            },
        )

    except Exception as exc:
        _log.error(f"Analysis job алдаа: {exc}", exc_info=True)
        publish(redis, entry_id, "error", str(exc)[:120])
        raise


# ── Job 3: Deep Insight ───────────────────────────────────────────────────────

def process_deep_insight(user_id: str) -> None:
    """
    ValueGraph-д тулгуурлан Deep Insight үүсгэж
    хэрэглэгчид push notification илгээнэ.
    10+ тэмдэглэлийн дараа автоматаар дуудагдана.
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


# ── Job 4: Human Insight (автомат) ───────────────────────────────────────────

def generate_human_insight_job(
    user_id: str, run_id: str, entry_id: str
) -> None:
    """
    Pattern Engine дуусмагц автоматаар дуудагдана.
    detected_patterns → LLM → human_insights хадгална → WS мэдэгдэл.
    Нэг run-д хоёр дахь удаа дуудагдвал кэш шалгаж алгасна.
    """
    from app.services.llm_service import get_llm_service
    from app.db.supabase import get_admin_client
    from app.db.redis_client import get_redis_connection

    db    = get_admin_client()
    redis = get_redis_connection()

    # Нэг run-д нэг л insight үүсгэнэ
    existing = (
        db.table("human_insights")
        .select("id")
        .eq("pattern_run_id", run_id)
        .execute()
    ).data or []

    if existing:
        _log.info(f"Human insight кэшлэгдсэн — алгасна: run_id={run_id}")
        return

    # Тухайн run-н хамгийн хүчтэй 5 pattern
    patterns = (
        db.table("detected_patterns")
        .select("pattern_type, pattern_data, strength_score")
        .eq("user_id", user_id)
        .eq("run_id", run_id)
        .order("strength_score", desc=True)
        .limit(5)
        .execute()
    ).data or []

    if not patterns:
        _log.warning(f"Human insight: pattern олдсонгүй run_id={run_id}")
        return

    try:
        result = run_async(
            get_llm_service().generate_human_insight(patterns)
        )
    except Exception as exc:
        _log.error(f"Human insight LLM алдаа: {exc}", exc_info=True)
        return

    top_strength = max(p.get("strength_score") or 0.0 for p in patterns)

    row = (
        db.table("human_insights")
        .insert(
            {
                "user_id":        user_id,
                "pattern_run_id": run_id,
                "insight_text":   result["insight_text"],
                "highlight_type": result.get("highlight_type", ""),
                "strength_score": top_strength,
            }
        )
        .execute()
    ).data[0]

    publish(
        redis, entry_id, "human_insight_ready",
        payload={
            "insight_id":     row["id"],
            "insight_text":   result["insight_text"],
            "highlight_type": result.get("highlight_type", ""),
        },
    )
    _log.info(f"Human Insight done: user={user_id}, run={run_id}")


# ── Private helpers ───────────────────────────────────────────────────────────

def _start_pattern_run(db, user_id: str) -> str:
    """pattern_runs-д шинэ мөр нэмж run_id буцаана."""
    row = (
        db.table("pattern_runs")
        .insert({"user_id": user_id, "status": "running"})
        .execute()
    ).data[0]
    return row["id"]