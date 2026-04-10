"""
Pattern Domain Entities - Pure Business Logic Objects for Pattern Detection (Flow 3)
These are NOT Pydantic models, they are plain dataclasses/objects.
Matches UML Design Classes: PatternDetector, PatternRule, Pattern
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass
class PatternRule:
    """
    Design Class: PatternRule
    Дүрэм тодорхойлолт - pattern detection-ийн суурь логикууд
    """
    rule_name: str
    rule_type: str  # e.g., "value_co_occurrence", "emotion_trend", "hawkins_shift"
    description: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def evaluate(self, graph_data: Dict[str, Any]) -> bool:
        """
        Evaluate if this rule matches the given graph data.
        Default implementation returns False (abstract method pattern).
        Subclasses should override this for specific rule logic.
        """
        # Default: no match - subclasses must implement
        return False


@dataclass
class Pattern:
    """
    Design Class: Pattern
    Илэрсэн хэв маяг
    """
    pattern_type: str
    description: str
    strength: float  # 0.0 to 1.0
    graph_id: UUID
    id: UUID = field(default_factory=uuid4)
    rule_id: Optional[UUID] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    
    def validate_pattern(self) -> bool:
        """Validate pattern integrity."""
        return self.strength > 0.0 and len(self.description) > 0


@dataclass
class PatternDetector:
    """
    Design Class: PatternDetector
    Graph-ээс pattern илрүүлэх үндсэн логик
    """
    rules: List[PatternRule] = field(default_factory=list)
    
    def add_rule(self, rule: PatternRule) -> None:
        """Add a pattern rule to the detector."""
        self.rules.append(rule)
    
    def detect_patterns(self, graph_data: Dict[str, Any]) -> List[Pattern]:
        """
        Detect patterns in the value graph.
        Returns list of detected patterns.
        """
        detected = []
        for rule in self.rules:
            if rule.is_active and rule.evaluate(graph_data):
                pattern = Pattern(
                    pattern_type=rule.rule_type,
                    description=f"Detected: {rule.rule_name}",
                    strength=0.8,  # Placeholder
                    graph_id=graph_data.get("graph_id"),
                    rule_id=rule.id
                )
                if pattern.validate_pattern():
                    detected.append(pattern)
        return detected
    
    def analyze_trend(self, user_id: UUID, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze trends for a user over time.
        Part of Flow 3: Pattern Detection & Recommendation
        """
        # Placeholder for trend analysis logic
        return {
            "user_id": str(user_id),
            "trend_summary": "Analysis pending implementation",
            "patterns_detected": len(historical_data)
        }


@dataclass
class RecommendationInsightEntity:
    """
    Design Class: RecommendationInsight (Domain Entity)
    Pattern дээр үндэслэсэн зөвлөмж
    """
    user_id: UUID
    insight_text: str
    recommendations: Dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    pattern_id: Optional[UUID] = None
    is_actioned: bool = False
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def mark_as_actioned(self) -> bool:
        """Mark recommendation as actioned by user."""
        self.is_actioned = True
        return True
    
    def dismiss(self) -> None:
        """Dismiss this recommendation."""
        self.is_actioned = False  # Or set a dismissed flag
