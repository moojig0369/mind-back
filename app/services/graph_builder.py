"""
GraphBuilder — ValueGraph CRUD үйлдлүүд.
JournalService-с тусгаарласан (SRP).

Архитектур:
  Maslow    → ValueNode   (need layer)
  Plutchik  → Emotion     (node дээр attach, confidence-weighted)
  Hawkins   → Edge        (value хоорондын energy, EWMA + recency decay)
  Tracker   → raw log
  Aggregated→ summarized state
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import combinations

from supabase import Client
from app.schemas.analysis import LlmAnalysisResult

# ── Тохиргоо ─────────────────────────────────────────────────────────────────
_EWMA_ALPHA        = 0.3    # Edge EWMA smoothing factor
_HAWKINS_PRIOR     = 200.0  # Neutral prior (Courage level) — cold start bias
_HAWKINS_PRIOR_SCR = 0.5    # Neutral prior score
_HALF_LIFE_DAYS    = 30.0   # Emotion recency decay — 30 хоногт жин хагасална
_WINDOW_DAYS       = 90     # Dominant emotion тооцох цонх (хоног)
_TRACKER_LIMIT     = 100    # Нэг emotion-н max tracker row
_MAX_NODES         = 8      # Нэг entry-н max node
_MAX_EDGES         = 10     # Нэг entry-н max edge (quadratic өсөлтөөс хамгаална)


@dataclass(frozen=True)
class _NodeSpec:
    category: str
    value: str
    confidence: float


class GraphBuilder:
    """ValueNode, ValueEdge болон Emotion tracker шинэчлэлт."""

    def __init__(self, db: Client) -> None:
        self._db = db

    # ── Public ───────────────────────────────────────────────────────────────

    def update_graph(
        self,
        user_id: str,
        analysis: LlmAnalysisResult,
        entry_id: str,
    ) -> None:
        """
        Single entry point — graph бүхэлд нь шинэчилнэ.

        1. Maslow → NodeSpec parse
        2. Nodes  → batch upsert
        3. Emotions → confidence-weighted attach
        4. Edges  → undirected, canonical, capped
        """
        specs = self._parse_specs(analysis)
        if not specs:
            return

        # 1. Nodes — batch upsert, confidence desc эрэмбэтэй
        node_map = self._batch_upsert_nodes(user_id, specs)
        # node_map: {(category, value): node_id}

        # 2. Emotions — confidence-weighted
        self._upsert_emotions_weighted(node_map, specs, entry_id, analysis)

        # 3. Edges — undirected, canonical pair, capped
        node_ids = list(node_map.values())
        pairs = list(combinations(node_ids, 2))[:_MAX_EDGES]
        for id_1, id_2 in pairs:
            self._upsert_edge(id_1, id_2, entry_id, analysis)

    def fetch_graph(self, user_id: str) -> dict:
        """v_user_graph view-г ашиглан React Flow граф буцаана."""
        rows = (
            self._db.table("v_user_graph")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        ).data or []
        return _rows_to_graph(rows)

    # ── Private: Parse ────────────────────────────────────────────────────────

    def _parse_specs(self, analysis: LlmAnalysisResult) -> list[_NodeSpec]:
        """
        LlmAnalysisResult-с NodeSpec жагсаалт үүсгэнэ.
        Confidence-аар буурах дарааллаар, MAX_NODES-оор хязгаарлана.
        """
        specs: list[_NodeSpec] = []
        for item in analysis.maslow:
            category = item.get("category", "")
            for value_dict in item.get("values", []):
                for value, conf in value_dict.items():
                    try:
                        specs.append(_NodeSpec(category, value, float(conf)))
                    except (TypeError, ValueError):
                        pass

        return sorted(specs, key=lambda s: s.confidence, reverse=True)[:_MAX_NODES]

    # ── Private: Node ─────────────────────────────────────────────────────────

    def _batch_upsert_nodes(
        self,
        user_id: str,
        specs: list[_NodeSpec],
    ) -> dict[tuple[str, str], str]:
        """
        Нэг SELECT-ээр бүх node-уудыг шалгаж,
        байгааг нь increment, байхгүйг нь insert хийнэ.

        Returns:
            {(category, value): node_id}
        """
        values = [s.value for s in specs]

        existing_rows = (
            self._db.table("value_nodes")
            .select("id, maslow_category, maslow_value, mention_count, confidence_sum")
            .eq("user_id", user_id)
            .in_("maslow_value", values)
            .execute()
        ).data or []

        existing: dict[tuple[str, str], dict] = {
            (r["maslow_category"], r["maslow_value"]): r
            for r in existing_rows
        }

        node_map: dict[tuple[str, str], str] = {}

        for spec in specs:
            key = (spec.category, spec.value)
            if key in existing:
                node_id = self._increment_node(existing[key], spec.confidence)
            else:
                node_id = self._create_node(user_id, spec)
                # Race condition-оос хамгаалж lookup-д нэмнэ
                existing[key] = {
                    "id":              node_id,
                    "maslow_category": spec.category,
                    "maslow_value":    spec.value,
                    "mention_count":   1,
                    "confidence_sum":  spec.confidence,
                }
            node_map[key] = node_id

        return node_map

    def _increment_node(self, node: dict, confidence: float) -> str:
        new_count  = node["mention_count"] + 1
        new_conf   = node["confidence_sum"] + confidence
        # weight = avg confidence (mention тоогоор жинлэсэн)
        new_weight = round(new_conf / new_count, 4)

        self._db.table("value_nodes").update({
            "mention_count":  new_count,
            "confidence_sum": round(new_conf, 4),
            "weight":         new_weight,
        }).eq("id", node["id"]).execute()

        return node["id"]

    def _create_node(self, user_id: str, spec: _NodeSpec) -> str:
        result = (
            self._db.table("value_nodes")
            .insert({
                "user_id":         user_id,
                "maslow_category": spec.category,
                "maslow_value":    spec.value,
                "mention_count":   1,
                "confidence_sum":  round(spec.confidence, 4),
                "weight":          round(spec.confidence, 4),
            })
            .execute()
        )
        return result.data[0]["id"]

    # ── Private: Edge (undirected) ────────────────────────────────────────────

    def _canonical_pair(self, id_1: str, id_2: str) -> tuple[str, str]:
        """
        UUID-г үргэлж нэг дарааллаар буцаана (node_a < node_b).
        DB-д CHECK constraint-тай хамт давхардал үүсэхгүй.
        """
        return (id_1, id_2) if id_1 < id_2 else (id_2, id_1)

    def _upsert_edge(
        self,
        id_1: str,
        id_2: str,
        entry_id: str,
        analysis: LlmAnalysisResult,
    ) -> None:
        """
        Undirected edge upsert + EWMA шинэчлэлт (α = 0.3).
        Шинэ edge-д neutral prior-оор warm-start хийнэ.
        value_edges_tracker-т raw log нэмнэ.
        """
        node_a, node_b = self._canonical_pair(id_1, id_2)
        h_level = analysis.hawkins.level
        h_score = analysis.hawkins.score

        existing = (
            self._db.table("value_edges")
            .select("id, hawkins_level_avg, hawkins_score_avg, interaction_count")
            .eq("node_a_id", node_a)
            .eq("node_b_id", node_b)
            .execute()
        ).data

        if existing:
            e = existing[0]
            new_level = round(
                _EWMA_ALPHA * h_level + (1 - _EWMA_ALPHA) * e["hawkins_level_avg"], 3
            )
            new_score = round(
                _EWMA_ALPHA * h_score + (1 - _EWMA_ALPHA) * e["hawkins_score_avg"], 4
            )
            self._db.table("value_edges").update({
                "hawkins_level_avg": new_level,
                "hawkins_score_avg": new_score,
                "interaction_count": e["interaction_count"] + 1,
            }).eq("id", e["id"]).execute()
            edge_id = e["id"]
        else:
            # Warm-start: prior-тай EWMA-г нэг алхам хийсэнтэй тэнцүү
            init_level = round(
                _EWMA_ALPHA * h_level + (1 - _EWMA_ALPHA) * _HAWKINS_PRIOR, 3
            )
            init_score = round(
                _EWMA_ALPHA * h_score + (1 - _EWMA_ALPHA) * _HAWKINS_PRIOR_SCR, 4
            )
            edge_id = (
                self._db.table("value_edges")
                .insert({
                    "node_a_id":         node_a,
                    "node_b_id":         node_b,
                    "hawkins_level_avg": init_level,
                    "hawkins_score_avg": init_score,
                    "interaction_count": 1,
                })
                .execute()
            ).data[0]["id"]

        self._db.table("value_edges_tracker").insert({
            "edge_id":       edge_id,
            "entry_id":      entry_id,
            "hawkins_level": h_level,
            "hawkins_score": h_score,
        }).execute()

    # ── Private: Emotion ──────────────────────────────────────────────────────

    def _upsert_emotions_weighted(
        self,
        node_map: dict[tuple[str, str], str],
        specs: list[_NodeSpec],
        entry_id: str,
        analysis: LlmAnalysisResult,
    ) -> None:
        """
        Emotion-ийг confidence-аар жинлэж node бүрт хуваарилна.

        - Хамгийн өндөр confidence-тай node → full primary + dyad авна
        - Бусад node → primary score нь confidence ratio-оор scale болно
        - Conflict flag → node-д тэмдэглэнэ
        """
        if not specs:
            return

        max_conf    = specs[0].confidence  # specs confidence desc эрэмбэтэй
        p           = analysis.plutchik
        is_conflict = getattr(p, "conflict_flag", False)

        # Нэг SELECT-ээр бүх node-н emotion-г batch авна
        node_ids = [node_map[k] for k in node_map]
        emotion_map = self._batch_get_or_create_emotions(node_ids)

        for rank, spec in enumerate(specs):
            key     = (spec.category, spec.value)
            node_id = node_map.get(key)
            if not node_id:
                continue

            emotion_id = emotion_map[node_id]

            # Confidence ratio-оор score scale
            ratio        = spec.confidence / max_conf if max_conf > 0 else 1.0
            scaled_score = round(p.primary_score * ratio, 4)

            # Dyad зөвхөн top node-д
            dyad       = p.dyad       if rank == 0 else None
            dyad_score = p.dyad_score if rank == 0 else None

            self._db.table("emotions_tracker").insert({
                "emotion_id":       emotion_id,
                "entry_id":         entry_id,
                "plutchik_primary": p.primary,
                "primary_score":    scaled_score,
                "plutchik_dyad":    dyad,
                "dyad_score":       dyad_score,
                "is_conflict":      is_conflict,
            }).execute()

            if is_conflict:
                self._db.rpc("increment_conflict_count", {
                    "p_node_id": node_id,
                }).execute()

            self._update_dominant_emotion(emotion_id)

    def _batch_get_or_create_emotions(
        self,
        node_ids: list[str],
    ) -> dict[str, str]:
        """
        node_id жагсаалтад харгалзах emotion_id-г нэг SELECT-ээр авна.
        Байхгүй node-уудад emotions мөр тус бүр insert хийнэ.

        Returns:
            {node_id: emotion_id}
        """
        # 1. Байгаа emotion-уудыг batch авна
        existing_rows = (
            self._db.table("emotions")
            .select("id, value_node_id")
            .in_("value_node_id", node_ids)
            .execute()
        ).data or []

        emotion_map: dict[str, str] = {
            r["value_node_id"]: r["id"]
            for r in existing_rows
        }

        # 2. Байхгүй node-уудад insert хийнэ
        missing = [nid for nid in node_ids if nid not in emotion_map]
        for node_id in missing:
            result = (
                self._db.table("emotions")
                .insert({"value_node_id": node_id, "total_entries": 0})
                .execute()
            )
            emotion_map[node_id] = result.data[0]["id"]

        return emotion_map

    def _update_dominant_emotion(self, emotion_id: str) -> None:
        """
        Сүүлийн _WINDOW_DAYS хоногийн tracker мэдээллээр
        exponential decay-weighted dominant тооцоолж emotions шинэчилнэ.

        decay = exp(-days_ago * ln(2) / half_life)
        → 30 хоногийн өмнөх утгын жин 0.5 болно
        """
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=_WINDOW_DAYS)
        ).isoformat()

        rows = (
            self._db.table("emotions_tracker")
            .select(
                "plutchik_primary, primary_score, "
                "plutchik_dyad, dyad_score, created_at"
            )
            .eq("emotion_id", emotion_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(_TRACKER_LIMIT)
            .execute()
        ).data or []

        if not rows:
            return

        now = datetime.now(timezone.utc)
        ln2 = math.log(2)

        primary_totals: dict[str, float] = {}
        dyad_totals:    dict[str, float] = {}
        total_weight = 0.0

        for r in rows:
            created  = datetime.fromisoformat(r["created_at"])
            days_ago = (now - created).total_seconds() / 86400
            decay    = math.exp(-days_ago * ln2 / _HALF_LIFE_DAYS)

            key = r["plutchik_primary"]
            primary_totals[key] = (
                primary_totals.get(key, 0) + r["primary_score"] * decay
            )
            total_weight += decay

            if r.get("plutchik_dyad") and r.get("dyad_score"):
                dk = r["plutchik_dyad"]
                dyad_totals[dk] = (
                    dyad_totals.get(dk, 0) + r["dyad_score"] * decay
                )

        if not primary_totals or total_weight == 0:
            return

        dominant_primary = max(primary_totals, key=primary_totals.__getitem__)
        dominant_primary_score = round(
            primary_totals[dominant_primary] / total_weight, 3
        )

        dominant_dyad = (
            max(dyad_totals, key=dyad_totals.__getitem__) if dyad_totals else None
        )
        dominant_dyad_score = (
            round(dyad_totals[dominant_dyad] / total_weight, 3)
            if dominant_dyad else None
        )

        self._db.table("emotions").update({
            "dominant_primary":       dominant_primary,
            "dominant_primary_score": dominant_primary_score,
            "dominant_dyad":          dominant_dyad,
            "dominant_dyad_score":    dominant_dyad_score,
            "total_entries":          len(rows),
        }).eq("id", emotion_id).execute()


# ── Module-level helper ───────────────────────────────────────────────────────

def _rows_to_graph(rows: list[dict]) -> dict:
    """
    v_user_graph view row-уудыг React Flow-д тохирох
    {nodes, edges} бүтэц рүү хөрвүүлнэ.
    """
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}

    for row in rows:
        nid = row["node_id"]
        if nid not in nodes:
            nodes[nid] = {
                "id":               nid,
                "maslow_category":  row["maslow_category"],
                "maslow_value":     row["maslow_value"],
                "weight":           row["weight"],
                "mention_count":    row["mention_count"],
                "dominant_primary": row["dominant_primary"],
                "dominant_dyad":    row["dominant_dyad"],
            }

        eid = row.get("edge_id")
        if eid and eid not in edges:
            edges[eid] = {
                "id":                eid,
                "node_a_id":         row["node_a_id"],
                "node_b_id":         row["node_b_id"],
                "hawkins_level_avg": row["hawkins_level_avg"],
                "hawkins_score_avg": row["hawkins_score_avg"],
                "interaction_count": row["interaction_count"],
            }

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}