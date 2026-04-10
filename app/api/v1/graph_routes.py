"""
Graph API Routes - Controller Layer
Provides endpoints for ValueGraph visualization and pattern analysis.
Optimized for frontend consumption with beautiful data structures.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from uuid import UUID

from app.infrastructure.database import get_db
from app.infrastructure.repositories.graph_repo import GraphRepository
from app.api.v1.deps import get_current_user
from app.api.v1.schemas.graph_schemas import (
    GraphSummarySchema,
    GraphVisualizationSchema,
    ValueNodeSchema,
    ValueEdgeSchema,
    PatternSchema,
    RecommendationSchema
)

router = APIRouter(prefix="/graph", tags=["ValueGraph"])


async def get_graph_repo(db=Depends(get_db)) -> GraphRepository:
    """Dependency factory for graph repository."""
    return GraphRepository(db)


@router.get("/summary", response_model=Dict[str, Any])
async def get_graph_summary(
    user: dict = Depends(get_current_user),
    repo: GraphRepository = Depends(get_graph_repo),
):
    """
    Get user's complete ValueGraph summary.
    Includes nodes, edges, patterns, recommendations, and statistics.
    Perfect for dashboard overview.
    """
    try:
        user_id = str(user["id"])
        
        # Get statistics
        stats = await repo.get_graph_statistics(user_id)
        
        # Get nodes and edges
        nodes = await repo.get_value_nodes(user_id)
        edges = await repo.get_value_edges(user_id)
        
        # Get patterns and recommendations
        patterns = await repo.get_patterns(user_id)
        recommendations = await repo.get_recommendations(user_id)
        
        # Determine emotional trend based on average Hawkins
        avg_hawkins = stats["avg_hawkins"]
        if avg_hawkins >= 350:
            emotional_trend = "thriving"
        elif avg_hawkins >= 250:
            emotional_trend = "stable"
        elif avg_hawkins >= 200:
            emotional_trend = "struggling"
        else:
            emotional_trend = "challenged"
        
        return {
            "user_id": user_id,
            "total_nodes": stats["total_nodes"],
            "total_edges": stats["total_edges"],
            "nodes": [ValueNodeSchema.model_validate(n).model_dump() for n in nodes],
            "edges": [ValueEdgeSchema.model_validate(e).model_dump() for e in edges],
            "patterns": [PatternSchema.model_validate(p).model_dump() for p in patterns],
            "recommendations": [RecommendationSchema.model_validate(r).model_dump() for r in recommendations],
            "dominant_values": stats["dominant_values"],
            "emotional_trend": emotional_trend,
            "hawkins_average": stats["avg_hawkins"],
            "maslow_distribution": stats["maslow_distribution"],
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph summary failed: {str(e)}")


@router.get("/visualization", response_model=GraphVisualizationSchema)
async def get_graph_visualization(
    user: dict = Depends(get_current_user),
    repo: GraphRepository = Depends(get_graph_repo),
):
    """
    Get graph data optimized for D3.js or similar visualization libraries.
    Returns nodes and links format ready for rendering.
    """
    try:
        user_id = str(user["id"])
        
        # Get nodes and edges
        nodes = await repo.get_value_nodes(user_id)
        edges = await repo.get_value_edges(user_id)
        
        # Get statistics for metadata
        stats = await repo.get_graph_statistics(user_id)
        
        # Transform to D3.js friendly format
        node_data = []
        for node in nodes:
            node_data.append({
                "id": str(node.id),
                "label": node.value,
                "value": node.weight * 100,  # Size by weight
                "group": node.maslow_code or "unknown",
                "color": get_maslow_color(node.maslow_code),
                "hawkins": node.avg_hawkins or 200,
                "mentions": node.mention_count,
            })
        
        link_data = []
        for edge in edges:
            link_data.append({
                "source": str(edge.source_node_id),
                "target": str(edge.target_node_id),
                "value": edge.weight,
                "strength": min(1.0, edge.weight / 10),  # Normalize for visualization
            })
        
        return GraphVisualizationSchema(
            nodes=node_data,
            links=link_data,
            metadata={
                "total_nodes": len(node_data),
                "total_edges": len(link_data),
                "avg_hawkins": stats["avg_hawkins"],
                "dominant_values": stats["dominant_values"],
                "maslow_distribution": stats["maslow_distribution"],
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visualization data failed: {str(e)}")


@router.get("/patterns", response_model=Dict[str, Any])
async def get_patterns(
    user: dict = Depends(get_current_user),
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Get detected behavioral patterns for user."""
    try:
        user_id = str(user["id"])
        patterns = await repo.get_patterns(user_id)
        
        return {
            "user_id": user_id,
            "patterns": [PatternSchema.model_validate(p).model_dump() for p in patterns],
            "count": len(patterns),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern retrieval failed: {str(e)}")


@router.get("/nodes", response_model=Dict[str, Any])
async def get_value_nodes(
    user: dict = Depends(get_current_user),
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Get all ValueNodes for user with weights and metadata."""
    try:
        user_id = str(user["id"])
        nodes = await repo.get_value_nodes(user_id)
        
        return {
            "user_id": user_id,
            "nodes": [ValueNodeSchema.model_validate(n).model_dump() for n in nodes],
            "count": len(nodes),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Node retrieval failed: {str(e)}")


@router.post("/recalculate", response_model=Dict[str, Any])
async def recalculate_graph(
    user: dict = Depends(get_current_user),
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Trigger manual graph recalculation for user."""
    try:
        user_id = str(user["id"])
        
        # TODO: Queue recalculation job via RQ
        # For now, just ensure graph exists
        await repo.get_or_create_graph(user_id)
        
        return {
            "user_id": user_id,
            "message": "Graph recalculation queued",
            "status": "queued"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")


def get_maslow_color(maslow_code: str | None) -> str:
    """Get color for Maslow category for visualization."""
    colors = {
        "physiological": "#FF6B6B",  # Red
        "safety": "#4ECDC4",         # Teal
        "social": "#45B7D1",         # Blue
        "esteem": "#FFA07A",         # Orange
        "self_actualization": "#98D8C8",  # Green
        "transcendence": "#F7DC6F",   # Yellow
    }
    return colors.get(maslow_code, "#95A5A6")  # Gray default
