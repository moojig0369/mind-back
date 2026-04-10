"""
Graph Domain Entities - Pure Business Logic Objects for Value Graph (Flow 2)
These are NOT Pydantic models, they are plain dataclasses/objects.
Matches UML Design Classes: ValueGraph, ValueNode, ValueEdge, and Trackers
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass
class ValueNodeMaslowTracker:
    """
    Design Class: ValueNodeMaslowTracker
    Tracks Maslow category associations for a value node
    """
    node_id: UUID
    journal_id: UUID
    maslow_code: str
    confidence_score: float
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def track_progress(self) -> Dict[str, Any]:
        """Track progress of this Maslow category association."""
        return {
            "node_id": str(self.node_id),
            "maslow_code": self.maslow_code,
            "confidence": self.confidence_score,
            "tracked_at": self.created_at.isoformat()
        }


@dataclass
class ValueNodeEmotionTracker:
    """
    Design Class: ValueNodeEmotionTracker
    Tracks emotion associations for a value node
    """
    node_id: UUID
    journal_id: UUID
    primary_emotion: str
    secondary_emotion: Optional[str] = None
    confidence_score: float = 0.0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_emotion_trend(self) -> str:
        """Get emotion trend description."""
        if self.secondary_emotion:
            return f"{self.primary_emotion} → {self.secondary_emotion}"
        return self.primary_emotion


@dataclass
class ValueEdgeTracker:
    """
    Design Class: ValueEdgeTracker
    Tracks correlation strength between value nodes
    """
    edge_id: UUID
    journal_id: UUID
    hawkins_level: int
    hawkins_score: float
    confidence_score: float
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def verify_correlation(self) -> bool:
        """Verify if the correlation is statistically significant."""
        return self.confidence_score > 0.5 and self.hawkins_score > 0.3


@dataclass
class ValueNode:
    """
    Design Class: ValueNode
    Represents a value in the user's value graph
    """
    value: str
    weight: float = 0.0
    avg_hawkins: Optional[float] = None
    mention_count: int = 0
    maslow_code: Optional[str] = None
    dominant_primary: Optional[str] = None
    graph_id: Optional[UUID] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Relationships
    emotion_trackers: List[ValueNodeEmotionTracker] = field(default_factory=list)
    maslow_trackers: List[ValueNodeMaslowTracker] = field(default_factory=list)
    
    def calculate_importance(self) -> float:
        """Calculate node importance based on weight and mention count."""
        return self.weight * (1 + self.mention_count / 10.0)
    
    def add_emotion_tracker(self, tracker: ValueNodeEmotionTracker) -> None:
        """Add an emotion tracker to this node."""
        self.emotion_trackers.append(tracker)
    
    def add_maslow_tracker(self, tracker: ValueNodeMaslowTracker) -> None:
        """Add a Maslow tracker to this node."""
        self.maslow_trackers.append(tracker)


@dataclass
class ValueEdge:
    """
    Design Class: ValueEdge
    Represents a connection between two value nodes
    """
    source_node_id: UUID
    target_node_id: UUID
    weight: float = 0.0
    graph_id: Optional[UUID] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Relationships
    trackers: List[ValueEdgeTracker] = field(default_factory=list)
    
    def strengthen(self, amount: float) -> None:
        """Strengthen the edge by a given amount."""
        self.weight = min(1.0, self.weight + amount)
    
    def add_tracker(self, tracker: ValueEdgeTracker) -> None:
        """Add a tracker to this edge."""
        self.trackers.append(tracker)


@dataclass
class ValueGraph:
    """
    Design Class: ValueGraph
    User's complete value graph with nodes and edges
    """
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Relationships
    nodes: List[ValueNode] = field(default_factory=list)
    edges: List[ValueEdge] = field(default_factory=list)
    
    def update(self, psychometric_data: Dict[str, Any]) -> bool:
        """
        Update graph with new psychometric analysis data.
        Returns True if update was successful.
        """
        # Placeholder for update logic
        self.updated_at = datetime.utcnow()
        return True
    
    def find_central_values(self, top_n: int = 5) -> List[ValueNode]:
        """Find the most central values by importance."""
        sorted_nodes = sorted(
            self.nodes,
            key=lambda n: n.calculate_importance(),
            reverse=True
        )
        return sorted_nodes[:top_n]
    
    def detect_patterns(self) -> List[Dict[str, Any]]:
        """Detect patterns in the graph structure."""
        # Placeholder for pattern detection
        return []
    
    def recalculate_edge_strengths(self) -> None:
        """Recalculate all edge strengths based on trackers."""
        for edge in self.edges:
            if edge.trackers:
                avg_confidence = sum(t.confidence_score for t in edge.trackers) / len(edge.trackers)
                edge.strengthen(avg_confidence * 0.1)
    
    def prune_weak_connections(self, threshold: float = 0.2) -> int:
        """
        Remove edges below the threshold.
        Returns number of pruned edges.
        """
        initial_count = len(self.edges)
        self.edges = [e for e in self.edges if e.weight >= threshold]
        return initial_count - len(self.edges)
    
    def add_node(self, node: ValueNode) -> None:
        """Add a node to the graph."""
        node.graph_id = self.id
        self.nodes.append(node)
    
    def add_edge(self, edge: ValueEdge) -> None:
        """Add an edge to the graph."""
        edge.graph_id = self.id
        self.edges.append(edge)
