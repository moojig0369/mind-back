"""
Graph Repository - Data Access Layer for ValueGraph.
Handles all database operations for graph visualization.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.infrastructure.models import (
    ValueGraphDB, ValueNodeDB, ValueEdgeDB, 
    PatternDB, RecommendationInsightDB,
    ValueNodeEmotionTrackerDB, ValueNodeMaslowTrackerDB
)


class GraphRepository:
    """Repository for ValueGraph operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_graph(self, user_id: str) -> ValueGraphDB:
        """Get existing graph or create new one for user."""
        result = await self.db.execute(
            select(ValueGraphDB).where(ValueGraphDB.user_id == user_id)
        )
        graph = result.scalar_one_or_none()
        
        if not graph:
            graph = ValueGraphDB(user_id=user_id)
            self.db.add(graph)
            await self.db.flush()
        
        return graph
    
    async def get_graph_with_nodes_edges(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete graph with nodes and edges for visualization."""
        graph_result = await self.db.execute(
            select(ValueGraphDB)
            .where(ValueGraphDB.user_id == user_id)
            .options(
                selectinload(ValueGraphDB.nodes),
                selectinload(ValueGraphDB.edges)
            )
        )
        graph = graph_result.scalar_one_or_none()
        
        if not graph:
            return None
        
        return {
            "graph": graph,
            "nodes": graph.nodes,
            "edges": graph.edges,
        }
    
    async def get_value_nodes(self, user_id: str) -> List[ValueNodeDB]:
        """Get all value nodes for user."""
        graph_result = await self.db.execute(
            select(ValueGraphDB).where(ValueGraphDB.user_id == user_id)
        )
        graph = graph_result.scalar_one_or_none()
        
        if not graph:
            return []
        
        result = await self.db.execute(
            select(ValueNodeDB)
            .where(ValueNodeDB.graph_id == graph.id)
            .order_by(ValueNodeDB.weight.desc())
        )
        return result.scalars().all()
    
    async def get_value_edges(self, user_id: str) -> List[ValueEdgeDB]:
        """Get all value edges for user."""
        graph_result = await self.db.execute(
            select(ValueGraphDB).where(ValueGraphDB.user_id == user_id)
        )
        graph = graph_result.scalar_one_or_none()
        
        if not graph:
            return []
        
        result = await self.db.execute(
            select(ValueEdgeDB)
            .where(ValueEdgeDB.graph_id == graph.id)
            .order_by(ValueEdgeDB.weight.desc())
        )
        return result.scalars().all()
    
    async def get_patterns(self, user_id: str) -> List[PatternDB]:
        """Get detected patterns for user."""
        graph_result = await self.db.execute(
            select(ValueGraphDB).where(ValueGraphDB.user_id == user_id)
        )
        graph = graph_result.scalar_one_or_none()
        
        if not graph:
            return []
        
        result = await self.db.execute(
            select(PatternDB)
            .where(PatternDB.graph_id == graph.id)
            .order_by(PatternDB.strength.desc())
        )
        return result.scalars().all()
    
    async def get_recommendations(self, user_id: str) -> List[RecommendationInsightDB]:
        """Get recommendations for user."""
        result = await self.db.execute(
            select(RecommendationInsightDB)
            .where(RecommendationInsightDB.user_id == user_id)
            .order_by(RecommendationInsightDB.generated_at.desc())
        )
        return result.scalars().all()
    
    async def get_graph_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get graph statistics for summary."""
        graph_result = await self.db.execute(
            select(ValueGraphDB).where(ValueGraphDB.user_id == user_id)
        )
        graph = graph_result.scalar_one_or_none()
        
        if not graph:
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "avg_hawkins": 0.0,
                "maslow_distribution": {},
                "dominant_values": [],
            }
        
        # Count nodes and edges
        node_count = await self.db.execute(
            select(func.count(ValueNodeDB.id)).where(ValueNodeDB.graph_id == graph.id)
        )
        edge_count = await self.db.execute(
            select(func.count(ValueEdgeDB.id)).where(ValueEdgeDB.graph_id == graph.id)
        )
        
        # Get average Hawkins level
        avg_hawkins_result = await self.db.execute(
            select(func.avg(ValueNodeDB.avg_hawkins)).where(ValueNodeDB.graph_id == graph.id)
        )
        avg_hawkins = avg_hawkins_result.scalar() or 0.0
        
        # Get Maslow distribution
        maslow_result = await self.db.execute(
            select(ValueNodeDB.maslow_code, func.count(ValueNodeDB.id))
            .where(ValueNodeDB.graph_id == graph.id)
            .group_by(ValueNodeDB.maslow_code)
        )
        maslow_dist = {row[0]: row[1] for row in maslow_result.all() if row[0]}
        
        # Get top values by weight
        top_nodes_result = await self.db.execute(
            select(ValueNodeDB.value)
            .where(ValueNodeDB.graph_id == graph.id)
            .order_by(ValueNodeDB.weight.desc())
            .limit(5)
        )
        dominant_values = [row[0] for row in top_nodes_result.all()]
        
        return {
            "total_nodes": node_count.scalar() or 0,
            "total_edges": edge_count.scalar() or 0,
            "avg_hawkins": float(avg_hawkins),
            "maslow_distribution": maslow_dist,
            "dominant_values": dominant_values,
        }
    
    async def update_node_weight(self, node_id: str, weight: float):
        """Update node weight."""
        result = await self.db.execute(
            select(ValueNodeDB).where(ValueNodeDB.id == node_id)
        )
        node = result.scalar_one_or_none()
        if node:
            node.weight = weight
            await self.db.flush()
    
    async def add_edge(self, graph_id: str, source_id: str, target_id: str, weight: float):
        """Add or update edge between nodes."""
        # Check if edge exists
        existing = await self.db.execute(
            select(ValueEdgeDB).where(
                and_(
                    ValueEdgeDB.graph_id == graph_id,
                    ValueEdgeDB.source_node_id == source_id,
                    ValueEdgeDB.target_node_id == target_id
                )
            )
        )
        edge = existing.scalar_one_or_none()
        
        if edge:
            edge.weight = weight
        else:
            edge = ValueEdgeDB(
                graph_id=graph_id,
                source_node_id=source_id,
                target_node_id=target_id,
                weight=weight
            )
            self.db.add(edge)
        
        await self.db.flush()
    
    async def create_pattern(
        self,
        graph_id: str,
        pattern_type: str,
        description: str,
        strength: float
    ) -> PatternDB:
        """Create new pattern."""
        pattern = PatternDB(
            graph_id=graph_id,
            pattern_type=pattern_type,
            description=description,
            strength=strength
        )
        self.db.add(pattern)
        await self.db.flush()
        return pattern
    
    async def create_recommendation(
        self,
        user_id: str,
        pattern_id: Optional[str],
        insight_text: str,
        recommendations: List[str]
    ) -> RecommendationInsightDB:
        """Create new recommendation."""
        import json
        rec = RecommendationInsightDB(
            user_id=user_id,
            pattern_id=pattern_id,
            insight_text=insight_text,
            recommendations=json.dumps(recommendations)
        )
        self.db.add(rec)
        await self.db.flush()
        return rec
