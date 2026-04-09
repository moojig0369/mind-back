"""
SQLAlchemy models for database tables.
Matches Migration V3 schema exactly.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index,
    CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class JournalEntryDB(Base):
    """journal_entries table."""
    
    __tablename__ = "journal_entries"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False, index=True)
    entry_index = Column(Integer, nullable=False)
    is_text_saved = Column(Boolean, default=False)
    surface_text = Column(Text)
    inner_reaction_text = Column(Text)
    meaning_text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    psychometric = relationship("PsychometricAnalysisDB", back_populates="journal", uselist=False)
    steps = relationship("JournalStepDB", back_populates="journal", uselist=False)
    
    __table_args__ = (
        UniqueConstraint("user_id", "entry_index", name="uq_journal_user_index"),
    )


class PsychometricAnalysisDB(Base):
    """psychometric_analyses table - Design class: PsychometricAnalysis."""
    
    __tablename__ = "psychometric_analyses"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    journal_id = Column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    maslow_categories = Column(ARRAY(String))
    plutchik_primary = Column(String, ForeignKey("ref_plutchik.emotion_key"))
    plutchik_dyad = Column(String)
    hawkins_level = Column(Integer, ForeignKey("ref_hawkins.level"))
    hawkins_label = Column(String)
    hawkins_confidence = Column(Float, CheckConstraint("hawkins_confidence BETWEEN 0 AND 1"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    journal = relationship("JournalEntryDB", back_populates="psychometric")
    logs = relationship("AnalysisLogDB", back_populates="analysis")
    
    __table_args__ = (
        UniqueConstraint("journal_id", name="uq_psychometric_journal"),
    )


class AnalysisLogDB(Base):
    """analysis_logs table - Design class: AnalysisLog."""
    
    __tablename__ = "analysis_logs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(PG_UUID(as_uuid=True), ForeignKey("psychometric_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String)
    duration = Column(Float)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    error = Column(Text)
    processed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    analysis = relationship("PsychometricAnalysisDB", back_populates="logs")


class ValueGraphDB(Base):
    """value_graphs table - Design class: ValueGraph."""
    
    __tablename__ = "value_graphs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nodes = relationship("ValueNodeDB", back_populates="graph")
    edges = relationship("ValueEdgeDB", back_populates="graph")


class ValueNodeDB(Base):
    """value_nodes table - Design class: ValueNode."""
    
    __tablename__ = "value_nodes"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_graphs.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(String, nullable=False)
    weight = Column(Float, default=0.0)
    avg_hawkins = Column(Float)
    mention_count = Column(Integer, default=0)
    maslow_category = Column(String)
    dominant_primary = Column(String, ForeignKey("ref_plutchik.emotion_key"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    graph = relationship("ValueGraphDB", back_populates="nodes")
    emotion_trackers = relationship("ValueNodeEmotionTrackerDB", back_populates="node")
    maslow_trackers = relationship("ValueNodeMaslowTrackerDB", back_populates="node")


class ValueEdgeDB(Base):
    """value_edges table - Design class: ValueEdge."""
    
    __tablename__ = "value_edges"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_graphs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_nodes.id"), nullable=False)
    target_node_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_nodes.id"), nullable=False)
    weight = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    graph = relationship("ValueGraphDB", back_populates="edges")
    trackers = relationship("ValueEdgeTrackerDB", back_populates="edge")


class ValueNodeEmotionTrackerDB(Base):
    """value_node_emotion_trackers table - Design class: ValueNodeEmotionTracker."""
    
    __tablename__ = "value_node_emotion_trackers"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    journal_id = Column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    primary_emotion = Column(String, ForeignKey("ref_plutchik.emotion_key"))
    secondary_emotion = Column(String, ForeignKey("ref_plutchik.emotion_key"))
    confidence_score = Column(Float, CheckConstraint("confidence_score BETWEEN 0 AND 1"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    node = relationship("ValueNodeDB", back_populates="emotion_trackers")


class ValueNodeMaslowTrackerDB(Base):
    """value_node_maslow_trackers table - Design class: ValueNodeMaslowTracker."""
    
    __tablename__ = "value_node_maslow_trackers"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    journal_id = Column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String, nullable=False)
    confidence_score = Column(Float, CheckConstraint("confidence_score BETWEEN 0 AND 1"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    node = relationship("ValueNodeDB", back_populates="maslow_trackers")


class ValueEdgeTrackerDB(Base):
    """value_edge_trackers table - Design class: ValueEdgeTracker."""
    
    __tablename__ = "value_edge_trackers"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    edge_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_edges.id", ondelete="CASCADE"), nullable=False, index=True)
    journal_id = Column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    hawkins_level = Column(Integer, ForeignKey("ref_hawkins.level"))
    hawkins_score = Column(Float, CheckConstraint("hawkins_score BETWEEN 0 AND 1"))
    confidence_score = Column(Float, CheckConstraint("confidence_score BETWEEN 0 AND 1"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    edge = relationship("ValueEdgeDB", back_populates="trackers")


class PatternRuleDB(Base):
    """pattern_rules table - Design class: PatternRule."""
    
    __tablename__ = "pattern_rules"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_name = Column(String, nullable=False, unique=True)
    rule_type = Column(String, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class PatternDB(Base):
    """patterns table - Design class: Pattern."""
    
    __tablename__ = "patterns"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id = Column(PG_UUID(as_uuid=True), ForeignKey("value_graphs.id", ondelete="CASCADE"), index=True)
    rule_id = Column(PG_UUID(as_uuid=True), ForeignKey("pattern_rules.id", ondelete="SET NULL"))
    pattern_type = Column(String, nullable=False)
    description = Column(Text)
    strength = Column(Float)
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    recommendation = relationship("RecommendationInsightDB", back_populates="pattern", uselist=False)


class RecommendationInsightDB(Base):
    """recommendation_insights table - Design class: RecommendationInsight."""
    
    __tablename__ = "recommendation_insights"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    pattern_id = Column(PG_UUID(as_uuid=True), ForeignKey("patterns.id"))
    insight_text = Column(Text, nullable=False)
    recommendations = Column(String)  # JSON as string
    is_actioned = Column(Boolean, default=False)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    pattern = relationship("PatternDB", back_populates="recommendation")
