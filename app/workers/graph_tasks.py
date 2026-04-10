"""
Graph Worker Tasks - Background jobs for ValueGraph processing.
Handles graph updates, pattern detection, and recommendation generation.
"""

from typing import Optional
import logging
from datetime import datetime

from app.infrastructure.supabase_client import get_admin_client
from app.infrastructure.redis_client import get_redis_connection
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.repositories.graph_repo import GraphRepository
from app.domains.journal.service import JournalService
from app.infrastructure.repositories.journal_repo import JournalRepository
from app.infrastructure.ai.client import LLMClient

_log = logging.getLogger(__name__)


def publish(redis_conn, channel: str, event_type: str, message: str, payload: Optional[dict] = None):
    """Publish event to Redis channel."""
    import json
    data = {
        "type": event_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if payload:
        data["payload"] = payload
    
    redis_conn.publish(channel, json.dumps(data))


async def update_value_graph(user_id: str) -> dict:
    """
    Update ValueGraph based on latest psychometric analyses.
    Creates/updates nodes and edges based on values extracted from journals.
    """
    db = AsyncSessionLocal()
    repo = GraphRepository(db)
    redis = get_redis_connection()
    
    try:
        _log.info(f"Updating ValueGraph for user={user_id}")
        publish(redis, f"user:{user_id}:graph", "graph_updating", "Граф шинэчилж байна...")
        
        # Get or create graph
        graph = await repo.get_or_create_graph(user_id)
        
        # TODO: Fetch latest analyses and extract values
        # For now, just return graph info
        stats = await repo.get_graph_statistics(user_id)
        
        publish(
            redis, 
            f"user:{user_id}:graph", 
            "graph_updated", 
            "Граф амжилттай шинэчлэгдлээ",
            payload=stats
        )
        
        _log.info(f"ValueGraph updated for user={user_id}")
        return {"status": "success", "graph_id": str(graph.id), **stats}
        
    except Exception as e:
        _log.error(f"Graph update failed: {e}", exc_info=True)
        publish(redis, f"user:{user_id}:graph", "graph_error", str(e)[:120])
        raise
    finally:
        await db.close()


async def detect_patterns(user_id: str) -> dict:
    """
    Detect behavioral patterns from ValueGraph.
    Uses LLM to analyze trends and generate insights.
    """
    db = AsyncSessionLocal()
    repo = GraphRepository(db)
    llm_client = LLMClient()
    redis = get_redis_connection()
    
    try:
        _log.info(f"Detecting patterns for user={user_id}")
        publish(redis, f"user:{user_id}:patterns", "pattern_detecting", "Хэв маяг илрүүлж байна...")
        
        # Get graph data
        graph_data = await repo.get_graph_with_nodes_edges(user_id)
        if not graph_data:
            return {"status": "no_graph", "message": "No graph data available"}
        
        # Build summary for LLM
        nodes = graph_data["nodes"]
        edges = graph_data["edges"]
        
        summary = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "top_values": [n.value for n in sorted(nodes, key=lambda x: x.weight, reverse=True)[:5]],
            "maslow_distribution": {},
            "emotional_themes": [],
        }
        
        # Aggregate Maslow categories
        for node in nodes:
            if node.maslow_code:
                summary["maslow_distribution"][node.maslow_code] = \
                    summary["maslow_distribution"].get(node.maslow_code, 0) + 1
        
        # Use LLM to detect patterns
        prompt = f"""
Хэрэглэгчийн үнэт зүйлсийн графын дүн шинжилгээ:
- Нийт үнэт зүйлс: {summary['total_nodes']}
- Холбоосууд: {summary['total_edges']}
- Тэргүүлэх үнэт зүйлс: {', '.join(summary['top_values'])}
- Масловын түвшин: {summary['maslow_distribution']}

Дараах хэв маягуудыг илрүүл:
1. Давтагдах сэтгэл хөдлөлийн загвар
2. Үнэт зүйлсийн хоорондын хамаарал
3. Хөгжлийн чиг хандлага

JSON форматтай хариул:
{{
  "patterns": [
    {{"type": "string", "description": "string", "strength": float}}
  ],
  "insights": ["string"]
}}
"""
        
        result = await llm_client.generate_json(prompt)
        
        # Save detected patterns to database
        patterns_saved = []
        for pattern_data in result.get("patterns", []):
            pattern = await repo.create_pattern(
                graph_id=str(graph_data["graph"].id),
                pattern_type=pattern_data.get("type", "unknown"),
                description=pattern_data.get("description", ""),
                strength=pattern_data.get("strength", 0.5)
            )
            patterns_saved.append(pattern)
        
        publish(
            redis,
            f"user:{user_id}:patterns",
            "patterns_detected",
            f"{len(patterns_saved)} хэв маяг илрэгдлээ",
            payload={"count": len(patterns_saved)}
        )
        
        _log.info(f"Patterns detected for user={user_id}: {len(patterns_saved)} found")
        return {
            "status": "success",
            "patterns_count": len(patterns_saved),
            "insights": result.get("insights", [])
        }
        
    except Exception as e:
        _log.error(f"Pattern detection failed: {e}", exc_info=True)
        publish(redis, f"user:{user_id}:patterns", "pattern_error", str(e)[:120])
        raise
    finally:
        await db.close()


async def generate_recommendations(user_id: str) -> dict:
    """
    Generate actionable recommendations based on detected patterns.
    Creates personalized insights for user growth.
    """
    db = AsyncSessionLocal()
    repo = GraphRepository(db)
    llm_client = LLMClient()
    redis = get_redis_connection()
    
    try:
        _log.info(f"Generating recommendations for user={user_id}")
        
        # Get latest patterns
        patterns = await repo.get_patterns(user_id)
        if not patterns:
            # Try to detect patterns first
            await detect_patterns(user_id)
            patterns = await repo.get_patterns(user_id)
        
        if not patterns:
            return {"status": "no_patterns", "message": "No patterns to base recommendations on"}
        
        # Build context for LLM
        pattern_context = "\n".join([
            f"- {p.pattern_type}: {p.description} (strength: {p.strength})"
            for p in patterns[:5]  # Top 5 patterns
        ])
        
        prompt = f"""
Хэрэглэгчийн илрүүлсэн хэв маягууд:
{pattern_context}

Эдгээр хэв маягт үндэслэн дараах зөвлөмжүүдийг боловсруул:
1. Тодорхой, гүйцэтгэхэд хялбар алхамууд
2. Сэтгэл зүйн өсөлтөд чиглэсэн зөвлөгөө
3. Дахин давтагдахгүй байх арга зам

JSON форматтай хариул:
{{
  "insight_text": "Нэгдсэн гүн шинжилгээний текст (2-3 өгүүлбэр)",
  "recommendations": ["зөвлөгөө 1", "зөвлөгөө 2", "зөвлөгөө 3"]
}}
"""
        
        result = await llm_client.generate_json(prompt)
        
        # Save recommendation
        recommendation = await repo.create_recommendation(
            user_id=user_id,
            pattern_id=str(patterns[0].id) if patterns else None,
            insight_text=result.get("insight_text", ""),
            recommendations=result.get("recommendations", [])
        )
        
        # Send notification
        publish(
            redis,
            f"user:{user_id}:notifications",
            "recommendation_ready",
            "Шинэ зөвлөмж бэлэн боллоо",
            payload={
                "insight_preview": result.get("insight_text", "")[:100],
                "recommendation_count": len(result.get("recommendations", []))
            }
        )
        
        _log.info(f"Recommendations generated for user={user_id}")
        return {
            "status": "success",
            "recommendation_id": str(recommendation.id),
            "insight_text": result.get("insight_text", ""),
            "recommendations": result.get("recommendations", [])
        }
        
    except Exception as e:
        _log.error(f"Recommendation generation failed: {e}", exc_info=True)
        publish(redis, f"user:{user_id}:recommendations", "recommendation_error", str(e)[:120])
        raise
    finally:
        await db.close()


# Sync wrappers for RQ (which doesn't support async directly)
def update_value_graph_sync(user_id: str) -> dict:
    """Synchronous wrapper for update_value_graph."""
    import asyncio
    return asyncio.run(update_value_graph(user_id))


def detect_patterns_sync(user_id: str) -> dict:
    """Synchronous wrapper for detect_patterns."""
    import asyncio
    return asyncio.run(detect_patterns(user_id))


def generate_recommendations_sync(user_id: str) -> dict:
    """Synchronous wrapper for generate_recommendations."""
    import asyncio
    return asyncio.run(generate_recommendations(user_id))
