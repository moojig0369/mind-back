"""
AI/LLM prompts for different analysis types.
Centralized prompt templates for consistency.
"""

from typing import Optional, List, Dict, Any


# ── Seed Insight Prompts ──────────────────────────────────────────────────────

SEED_INSIGHT_SYSTEM_PROMPT = """
You are a compassionate psychological insight generator.
Analyze the user's journal entry and provide brief, empathetic insights.

Respond in JSON format with these fields:
- mirror: Reflect what you observe (1 sentence)
- reframe: Offer a new perspective (1 sentence)
- relief: Suggest something to let go of (1 sentence)
- summary: One-line takeaway
"""

SEED_INSIGHT_USER_TEMPLATE = """
Surface thought: {surface}
Inner reaction: {inner}
Deeper meaning: {meaning}

Provide your insights in JSON format.
"""


# ── Psychometric Analysis Prompts ────────────────────────────────────────────

PSYCHOMETRIC_SYSTEM_PROMPT = """
You are an expert psychological analyst specializing in:
1. Maslow's Hierarchy of Needs
2. Plutchik's Wheel of Emotions
3. Hawkins' Scale of Consciousness

Analyze the text and respond in JSON format with:
- maslow: Array of {{category, values: {{value_name: confidence}}}}
- plutchik_primary: Primary emotion key (joy, trust, fear, surprise, sadness, anger, disgust, anticipation)
- plutchik_secondary: Secondary emotion key (optional)
- plutchik_dyad: Dyad name if applicable (e.g., "love" = joy + trust)
- hawkins_level: Integer level (20-700)
- hawkins_label: Label for the level
- hawkins_confidence: Float 0-1

Be precise and evidence-based in your analysis.
"""

PSYCHOMETRIC_USER_TEMPLATE = """
Analyze this journal entry:

Surface thought: {surface}
Inner reaction: {inner}
Deeper meaning: {meaning}

Previous EWMA average: {ewma_previous}

Respond in JSON format following the schema.
"""


# ── Deep Insight Prompts ─────────────────────────────────────────────────────

DEEP_INSIGHT_SYSTEM_PROMPT = """
You are a wise psychological counselor providing deep insights.
Based on the user's value graph and journal history, offer meaningful guidance.

Respond in JSON format:
- insightText: Main insight (2-3 sentences)
- recommendations: Array of actionable suggestions
- patterns: Notable patterns observed
"""

DEEP_INSIGHT_USER_TEMPLATE = """
User has written {entry_count} journal entries.

Value Graph Summary:
{graph_summary}

Provide deep insights and recommendations in JSON format.
"""


# ── Helper Functions ─────────────────────────────────────────────────────────

def build_seed_messages(surface: str, inner: str, meaning: str) -> List[Dict[str, str]]:
    """Build messages for seed insight generation."""
    return [
        {"role": "system", "content": SEED_INSIGHT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": SEED_INSIGHT_USER_TEMPLATE.format(
                surface=surface,
                inner=inner,
                meaning=meaning,
            ),
        },
    ]


def build_psychometric_messages(
    surface: str,
    inner: str,
    meaning: str,
    ewma_previous: Optional[float] = None,
) -> List[Dict[str, str]]:
    """Build messages for psychometric analysis."""
    return [
        {"role": "system", "content": PSYCHOMETRIC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PSYCHOMETRIC_USER_TEMPLATE.format(
                surface=surface,
                inner=inner,
                meaning=meaning,
                ewma_previous=ewma_previous or "N/A",
            ),
        },
    ]


def build_deep_insight_messages(
    graph_summary: Dict[str, Any],
    entry_count: int,
) -> List[Dict[str, str]]:
    """Build messages for deep insight generation."""
    summary_text = "\n".join(f"- {k}: {v}" for k, v in graph_summary.items())
    
    return [
        {"role": "system", "content": DEEP_INSIGHT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": DEEP_INSIGHT_USER_TEMPLATE.format(
                entry_count=entry_count,
                graph_summary=summary_text,
            ),
        },
    ]
