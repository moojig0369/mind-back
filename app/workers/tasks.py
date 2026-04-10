"""
RQ Tasks for background job processing.
These tasks are enqueued by API routes and executed by workers.
"""

import logging
from typing import Dict, Any

_log = logging.getLogger(__name__)


def run_psychometric_analysis(
    entry_id: str, 
    user_id: str, 
    entry_text: Dict[str, str]
) -> None:
    """
    Enqueue the full psychometric analysis job.
    This wraps the jobs.run_analysis_job function for RQ compatibility.
    """
    from app.workers.jobs import run_analysis_job
    
    try:
        _log.info(f"Starting psychometric analysis: entry={entry_id}, user={user_id}")
        run_analysis_job(
            entry_id=entry_id,
            user_id=user_id,
            entry_text=entry_text
        )
        _log.info(f"Psychometric analysis completed: entry={entry_id}")
    except Exception as exc:
        _log.error(f"Psychometric analysis failed: {exc}", exc_info=True)
        raise


def schedule_deep_insight(user_id: str) -> None:
    """
    Check if user is eligible for Deep Insight and queue if needed.
    Called by scheduler or after analysis completion.
    """
    from app.infrastructure.supabase_client import get_admin_client
    from app.infrastructure.redis_client import get_redis_connection, get_deep_insight_queue
    from app.infrastructure.repositories.journal_repo import JournalRepository
    from app.domains.journal.service import JournalService
    from app.infrastructure.ai.client import LLMClient
    from rq import Queue
    from redis import Redis
    from app.core.settings import settings
    
    db = get_admin_client()
    repo = JournalRepository(db)
    llm_client = LLMClient()
    journal = JournalService(repo, llm_client)
    redis = get_redis_connection()
    
    try:
        count = journal.count_user_entries(user_id)
        
        # Check if user is eligible (10+ entries, every 5th entry)
        if journal.should_trigger_deep_insight(count):
            _log.info(f"User {user_id} eligible for Deep Insight (count={count})")
            
            # Use RQ queue directly
            redis_client = Redis.from_url(settings.redis_url)
            queue = Queue(get_deep_insight_queue(), connection=redis_client)
            queue.enqueue(
                "app.workers.jobs.process_deep_insight",
                user_id=user_id,
                job_timeout=300,  # 5 minutes timeout
            )
            
            # Publish notification that insight is being generated
            from app.workers.job_helpers import publish
            publish(
                redis,
                f"user:{user_id}:notifications",
                "deep_insight_generating",
                "Гүн шинжилгээ бэлдэж байна...",
            )
        else:
            _log.debug(f"User {user_id} not eligible for Deep Insight (count={count})")
            
    except Exception as exc:
        _log.error(f"Deep Insight scheduling failed: {exc}", exc_info=True)
        raise
