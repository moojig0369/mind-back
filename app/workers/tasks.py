"""
Celery Tasks for Async Processing
Retry-safe background jobs for AI analysis and graph building.
"""
import logging
from typing import Dict, Any
from celery import Task
from app.workers.celery_app import celery_app
from app.core.exceptions import AIProcessingException

logger = logging.getLogger(__name__)


class AnalysisTask(Task):
    """Base task with retry logic for analysis jobs."""
    
    autoretry_for = (AIProcessingException,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log failure with full context."""
        logger.error(
            f"Task {task_id} failed: {exc}",
            extra={"args": args, "kwargs": kwargs},
        )


@celery_app.task(base=AnalysisTask, bind=True)
def run_psychometric_analysis(
    self,
    entry_id: str,
    user_id: str,
    entry_text: Dict[str, str],
) -> Dict[str, Any]:
    """
    Run full psychometric analysis on a journal entry.
    
    Pipeline:
    1. Extract text from entry
    2. Call LLM for analysis
    3. Save results to psychometric_analyses table
    4. Log performance metrics
    5. Update value graph
    """
    try:
        logger.info(f"Starting analysis for entry {entry_id}")
        
        # Import here to avoid circular imports
        from app.infrastructure.ai.client import LLMClient
        from app.domains.insight.service import InsightService
        from app.infrastructure.repositories.analysis_repo import AnalysisRepository
        from app.infrastructure.database import get_supabase_client
        
        # Get DB client
        db = get_supabase_client()
        analysis_repo = AnalysisRepository(db)
        
        # Create pending analysis record
        analysis = analysis_repo.create_pending(entry_id, user_id)
        
        # Run LLM analysis
        llm = LLMClient()
        result = await llm.analyze_psychometrics(
            surface=entry_text.get("surface", ""),
            inner=entry_text.get("inner", ""),
            meaning=entry_text.get("meaning", ""),
        )
        
        # Complete analysis
        analysis.complete(
            maslow_categories=result.maslow,
            hawkins_level=result.hawkins_level,
            hawkins_label=result.hawkins_label,
            hawkins_confidence=result.hawkins_confidence,
            plutchik_primary=result.primary_emotion,
            plutchik_dyad=result.dyad,
        )
        
        analysis_repo.save(analysis)
        
        # Trigger graph update
        update_value_graph.delay(user_id=user_id, entry_id=entry_id)
        
        logger.info(f"Analysis completed for entry {entry_id}")
        
        return {
            "status": "success",
            "analysis_id": str(analysis.id),
            "entry_id": entry_id,
        }
        
    except Exception as e:
        logger.exception(f"Analysis failed for entry {entry_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(base=AnalysisTask, bind=True)
def update_value_graph(
    self,
    user_id: str,
    entry_id: str,
) -> Dict[str, Any]:
    """
    Update user's value graph based on new analysis.
    
    This task:
    1. Fetch latest psychometric analysis
    2. Extract values and emotions
    3. Update value nodes and edges
    4. Detect patterns
    """
    try:
        logger.info(f"Updating value graph for user {user_id}")
        
        from app.domains.graph.service import GraphService
        from app.infrastructure.repositories.graph_repo import GraphRepository
        from app.infrastructure.database import get_supabase_client
        
        db = get_supabase_client()
        graph_repo = GraphRepository(db)
        graph_service = GraphService(graph_repo)
        
        # Update graph with new analysis data
        graph_service.rebuild_user_graph(user_id, entry_id)
        
        logger.info(f"Value graph updated for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "entry_id": entry_id,
        }
        
    except Exception as e:
        logger.exception(f"Graph update failed for user {user_id}: {e}")
        raise self.retry(exc=e)
