"""
Graph API Routes - Controller Layer
Provides endpoints for ValueGraph visualization and pattern analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from app.domains.journal.service import JournalService
from app.api.v1.deps import get_journal_service, get_current_user

router = APIRouter(prefix="/graph", tags=["ValueGraph"])


def _get_journal_service() -> JournalService:
    """Dependency factory for journal service."""
    return get_journal_service()


@router.get("/summary")
async def get_graph_summary(
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Get user's ValueGraph summary including nodes, edges, and patterns."""
    try:
        summary = service.build_graph_summary(user["id"])
        return {
            "user_id": user["id"],
            "summary": summary,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph summary failed: {str(e)}")


@router.get("/patterns")
async def get_patterns(
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Get detected behavioral patterns for user."""
    try:
        # TODO: Implement pattern detection
        patterns = []
        return {
            "user_id": user["id"],
            "patterns": patterns,
            "count": len(patterns),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern retrieval failed: {str(e)}")


@router.get("/nodes")
async def get_value_nodes(
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Get all ValueNodes for user with weights and metadata."""
    try:
        # TODO: Implement node retrieval from repository
        nodes = []
        return {
            "user_id": user["id"],
            "nodes": nodes,
            "count": len(nodes),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Node retrieval failed: {str(e)}")


@router.post("/recalculate")
async def recalculate_graph(
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Trigger manual graph recalculation for user."""
    try:
        # TODO: Queue recalculation job
        return {
            "user_id": user["id"],
            "message": "Graph recalculation queued",
            "status": "queued"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")
