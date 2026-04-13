"""
PatternEngine — pattern_rules-г уншиж, detected_patterns-д бичнэ.

Дэмжих rule_type-ууд:
  aggregation — хамгийн их давтагдсан node/emotion
  threshold   — hawkins/intensity босго шалгах
  edge        — хүчтэй холбоо
  state       — нийт hawkins түвшин
  trend       — цаг хугацааны чиглэл
  variance    — савлалт/тогтворгүй байдал

Нэмэлт тохиргоо (pattern_rules.pattern_config):
  aggregation : top_n, metric (weight | mention_count)
  threshold   : hawkins_below, intensity_above, min_occurrence
  edge        : top_n, min_interaction
  state       : hawkins_below, min_entries
  trend       : window_days
  variance    : variance_threshold, window_days
"""

import logging
import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

_log = logging.getLogger(__name__)


class PatternEngine:
    """Хэрэглэгчийн graph/analysis өгөгдлөөс pattern илрүүлнэ."""

    def __init__(self, db: Client) -> None:
        self._db = db

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, user_id: str, run_id: str) -> list[dict]:
        """
        Идэвхтэй бүх pattern_rules-г ажиллуулж
        detected_patterns-д хадгална.

        Returns:
            Илрүүлсэн pattern-уудын жагсаалт
        """
        rules = self._fetch_active_rules()
        if not rules:
            _log.info("Pattern rules олдсонгүй, алгасана.")
            return []

        detected: list[dict] = []

        for rule in rules:
            try:
                result = self._run_rule(user_id, rule)
                if result:
                    detected.append(result)
            except Exception as exc:
                _log.error(
                    f"Rule '{rule['rule_name']}' алдаа: {exc}", exc_info=True
                )

        if detected:
            self._store_patterns(user_id, run_id, detected)
            _log.info(
                f"Pattern хадгаллаа: user={user_id}, "
                f"count={len(detected)}"
            )

        self._finish_run(run_id, status="completed")
        return detected

    # ── Rule dispatcher ───────────────────────────────────────────────────────

    def _run_rule(self, user_id: str, rule: dict) -> dict | None:
        """rule_type-аар зохих handler руу шилжүүлнэ."""
        rtype = rule.get("rule_type", "")
        cfg: dict = rule.get("pattern_config") or {}

        handlers = {
            "aggregation": self._agg_rule,
            "threshold":   self._threshold_rule,
            "edge":        self._edge_rule,
            "state":       self._state_rule,
            "trend":       self._trend_rule,
            "variance":    self._variance_rule,
        }

        handler = handlers.get(rtype)
        if not handler:
            _log.warning(f"Тодорхойлогдоогүй rule_type='{rtype}'")
            return None

        return handler(user_id, rule, cfg)

    # ── aggregation ──────────────────────────────────────────────────────────

    def _agg_rule(
        self, user_id: str, rule: dict, cfg: dict
    ) -> dict | None:
        """
        dominant_need  → value_nodes-г weight-аар эрэмбэлнэ
        dominant_emotion → emotions-г dominant_primary_score-аар эрэмбэлнэ
        """
        top_n  = int(cfg.get("top_n", 1))
        metric = cfg.get("metric", "weight")   # dominant_need-д ашиглана
        name   = rule["rule_name"]

        if "emotion" in name:
            rows = self._fetch_dominant_emotions(user_id)
            if not rows:
                return None
            top = sorted(
                rows,
                key=lambda r: r.get("dominant_primary_score") or 0,
                reverse=True,
            )[:top_n]
            strength = top[0].get("dominant_primary_score") or 0.0
            return self._make_result(
                rule,
                pattern_data={
                    "top_emotions": [
                        {
                            "node_id":    r["value_node_id"],
                            "emotion":    r["dominant_primary"],
                            "score":      r["dominant_primary_score"],
                        }
                        for r in top
                    ]
                },
                strength=strength,
                node_ids=[r["value_node_id"] for r in top],
            )
        else:
            # need / node aggregation
            rows = self._fetch_nodes(user_id)
            if not rows:
                return None
            top = sorted(
                rows,
                key=lambda r: r.get(metric) or 0,
                reverse=True,
            )[:top_n]
            strength = round((top[0].get(metric) or 0.0), 4)
            return self._make_result(
                rule,
                pattern_data={
                    "top_needs": [
                        {
                            "node_id":  r["id"],
                            "category": r["maslow_category"],
                            "value":    r["maslow_value"],
                            metric:     r.get(metric),
                        }
                        for r in top
                    ]
                },
                strength=min(strength, 1.0),
                node_ids=[r["id"] for r in top],
            )

    # ── threshold ────────────────────────────────────────────────────────────

    def _threshold_rule(
        self, user_id: str, rule: dict, cfg: dict
    ) -> dict | None:
        """
        unmet_need        → hawkins_below + min_occurrence (node-уудад)
        high_intensity_emotion → intensity_above + min_occurrence (tracker)
        """
        name = rule["rule_name"]

        if "emotion" in name:
            intensity_above = float(cfg.get("intensity_above", 0.7))
            min_occ         = int(cfg.get("min_occurrence", 2))

            rows = self._fetch_high_intensity_emotions(
                user_id, intensity_above, min_occ
            )
            if not rows:
                return None

            strength = max(r.get("avg_score") or 0 for r in rows)
            return self._make_result(
                rule,
                pattern_data={"high_intensity_emotions": rows},
                strength=min(float(strength), 1.0),
            )
        else:
            # unmet_need — value_edges-н hawkins_level_avg-г ашиглана
            hawkins_below = float(cfg.get("hawkins_below", 200))
            min_occ       = int(cfg.get("min_occurrence", 3))

            nodes = self._fetch_nodes(user_id)
            unmet = [
                n for n in nodes
                if (n.get("mention_count") or 0) >= min_occ
            ]

            # Node-тэй холбоотой edge-н hawkins_level_avg < босго
            unmet_detail = []
            for n in unmet:
                avg = self._avg_hawkins_for_node(n["id"])
                if avg is not None and avg < hawkins_below:
                    unmet_detail.append(
                        {
                            "node_id":      n["id"],
                            "category":     n["maslow_category"],
                            "value":        n["maslow_value"],
                            "mention_count": n["mention_count"],
                            "hawkins_avg":  avg,
                        }
                    )

            if not unmet_detail:
                return None

            strength = round(
                1.0 - min(d["hawkins_avg"] for d in unmet_detail) / 1000.0,
                4,
            )
            return self._make_result(
                rule,
                pattern_data={"unmet_needs": unmet_detail},
                strength=min(strength, 1.0),
                node_ids=[d["node_id"] for d in unmet_detail],
            )

    # ── edge ─────────────────────────────────────────────────────────────────

    def _edge_rule(
        self, user_id: str, rule: dict, cfg: dict
    ) -> dict | None:
        """strong_need_connection — interaction_count-аар top edge."""
        top_n        = int(cfg.get("top_n", 1))
        min_interact = int(cfg.get("min_interaction", 3))

        rows = self._fetch_edges(user_id, min_interact)
        if not rows:
            return None

        top = sorted(
            rows,
            key=lambda r: r.get("interaction_count") or 0,
            reverse=True,
        )[:top_n]

        strength = round(
            min((top[0].get("interaction_count") or 0) / 20.0, 1.0), 4
        )
        return self._make_result(
            rule,
            pattern_data={"strong_connections": top},
            strength=strength,
        )

    # ── state ────────────────────────────────────────────────────────────────

    def _state_rule(
        self, user_id: str, rule: dict, cfg: dict
    ) -> dict | None:
        """low_state — сүүлийн N тэмдэглэлийн hawkins_level дундаж."""
        hawkins_below = float(cfg.get("hawkins_below", 200))
        min_entries   = int(cfg.get("min_entries", 3))

        rows = self._fetch_recent_analyses(user_id, limit=min_entries * 2)
        if len(rows) < min_entries:
            return None

        levels = [r["hawkins_level"] for r in rows if r.get("hawkins_level")]
        if len(levels) < min_entries:
            return None

        avg = statistics.mean(levels)
        if avg >= hawkins_below:
            return None

        strength = round(1.0 - avg / 1000.0, 4)
        return self._make_result(
            rule,
            pattern_data={
                "hawkins_avg": round(avg, 2),
                "sample_size": len(levels),
                "threshold":   hawkins_below,
            },
            strength=min(strength, 1.0),
        )

    # ── trend ────────────────────────────────────────────────────────────────

    def _trend_rule(
        self, user_id: str, rule: dict, cfg: dict
    ) -> dict | None:
        """emotion_trend — window_days дотор primary_score-н чиглэл."""
        window = int(cfg.get("window_days", 7))
        rows   = self._fetch_emotion_tracker_window(user_id, window)
        if len(rows) < 3:
            return None

        scores = [r["primary_score"] for r in rows if r.get("primary_score") is not None]
        if len(scores) < 3:
            return None

        # Энгийн шугаман регресс (x = индекс)
        n      = len(scores)
        x_mean = (n - 1) / 2.0
        y_mean = statistics.mean(scores)
        num    = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
        den    = sum((i - x_mean) ** 2 for i in range(n))
        slope  = num / den if den != 0 else 0.0

        direction = "rising" if slope > 0.01 else "falling" if slope < -0.01 else "stable"
        strength  = min(abs(slope) * 10, 1.0)

        return self._make_result(
            rule,
            pattern_data={
                "direction":   direction,
                "slope":       round(slope, 6),
                "window_days": window,
                "sample_size": n,
            },
            strength=round(strength, 4),
        )

    # ── variance ─────────────────────────────────────────────────────────────

    def _variance_rule(
        self, user_id: str, rule: dict, cfg: dict
    ) -> dict | None:
        """emotion_variance — primary_score-н стандарт хазайлт."""
        threshold    = float(cfg.get("variance_threshold", 0.3))
        window       = int(cfg.get("window_days", 5))

        rows   = self._fetch_emotion_tracker_window(user_id, window)
        scores = [r["primary_score"] for r in rows if r.get("primary_score") is not None]
        if len(scores) < 3:
            return None

        stdev = statistics.stdev(scores)
        if stdev < threshold:
            return None

        strength = min(stdev / 1.0, 1.0)
        return self._make_result(
            rule,
            pattern_data={
                "stdev":       round(stdev, 4),
                "threshold":   threshold,
                "window_days": window,
                "sample_size": len(scores),
            },
            strength=round(strength, 4),
        )

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _fetch_active_rules(self) -> list[dict]:
        return (
            self._db.table("pattern_rules")
            .select("id, rule_name, rule_type, description, pattern_config, window_days")
            .eq("is_active", True)
            .execute()
        ).data or []

    def _fetch_nodes(self, user_id: str) -> list[dict]:
        return (
            self._db.table("value_nodes")
            .select("id, maslow_category, maslow_value, weight, mention_count")
            .eq("user_id", user_id)
            .execute()
        ).data or []

    def _fetch_dominant_emotions(self, user_id: str) -> list[dict]:
        """user_id-тай node-уудад харгалзах emotions авна."""
        node_ids = [
            r["id"]
            for r in self._fetch_nodes(user_id)
        ]
        if not node_ids:
            return []
        return (
            self._db.table("emotions")
            .select(
                "id, value_node_id, dominant_primary, "
                "dominant_primary_score, dominant_dyad"
            )
            .in_("value_node_id", node_ids)
            .not_.is_("dominant_primary", "null")
            .execute()
        ).data or []

    def _fetch_edges(self, user_id: str, min_interaction: int) -> list[dict]:
        """user-н node-уудтай холбоотой value_edges."""
        node_ids = [r["id"] for r in self._fetch_nodes(user_id)]
        if not node_ids:
            return []
        return (
            self._db.table("value_edges")
            .select(
                "id, node_a_id, node_b_id, "
                "hawkins_level_avg, interaction_count"
            )
            .in_("node_a_id", node_ids)
            .gte("interaction_count", min_interaction)
            .execute()
        ).data or []

    def _avg_hawkins_for_node(self, node_id: str) -> float | None:
        """Нэг node-тай холбоотой value_edges-н hawkins_level_avg дундаж."""
        rows = (
            self._db.table("value_edges")
            .select("hawkins_level_avg")
            .or_(f"node_a_id.eq.{node_id},node_b_id.eq.{node_id}")
            .execute()
        ).data or []
        levels = [r["hawkins_level_avg"] for r in rows if r.get("hawkins_level_avg")]
        return statistics.mean(levels) if levels else None

    def _fetch_recent_analyses(self, user_id: str, limit: int = 10) -> list[dict]:
        return (
            self._db.table("journal_analyses")
            .select(
                "hawkins_level, hawkins_score, "
                "journal_entries!inner(user_id)"
            )
            .eq("journal_entries.user_id", user_id)
            .order("processed_at", desc=True)
            .limit(limit)
            .execute()
        ).data or []

    def _fetch_high_intensity_emotions(
        self,
        user_id: str,
        intensity_above: float,
        min_occurrence: int,
    ) -> list[dict]:
        """emotions_tracker-с өндөр intensity-тай emotion бүлэглэнэ."""
        node_ids = [r["id"] for r in self._fetch_nodes(user_id)]
        if not node_ids:
            return []

        emotion_ids = [
            r["id"]
            for r in (
                self._db.table("emotions")
                .select("id")
                .in_("value_node_id", node_ids)
                .execute()
            ).data or []
        ]
        if not emotion_ids:
            return []

        rows = (
            self._db.table("emotions_tracker")
            .select("plutchik_primary, primary_score, emotion_id")
            .in_("emotion_id", emotion_ids)
            .gte("primary_score", intensity_above)
            .execute()
        ).data or []

        # Group by plutchik_primary
        grouped: dict[str, list[float]] = {}
        for r in rows:
            key = r["plutchik_primary"]
            grouped.setdefault(key, []).append(r["primary_score"])

        result = []
        for emotion, scores in grouped.items():
            if len(scores) >= min_occurrence:
                result.append(
                    {
                        "emotion":     emotion,
                        "count":       len(scores),
                        "avg_score":   round(statistics.mean(scores), 4),
                    }
                )

        return sorted(result, key=lambda r: r["avg_score"], reverse=True)

    def _fetch_emotion_tracker_window(
        self, user_id: str, window_days: int
    ) -> list[dict]:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=window_days)
        ).isoformat()

        node_ids = [r["id"] for r in self._fetch_nodes(user_id)]
        if not node_ids:
            return []

        emotion_ids = [
            r["id"]
            for r in (
                self._db.table("emotions")
                .select("id")
                .in_("value_node_id", node_ids)
                .execute()
            ).data or []
        ]
        if not emotion_ids:
            return []

        return (
            self._db.table("emotions_tracker")
            .select("plutchik_primary, primary_score, created_at")
            .in_("emotion_id", emotion_ids)
            .gte("created_at", cutoff)
            .order("created_at", desc=False)
            .execute()
        ).data or []

    # ── Store ─────────────────────────────────────────────────────────────────

    def _store_patterns(
        self,
        user_id: str,
        run_id: str,
        detected: list[dict],
    ) -> None:
        """detected_patterns-д batch insert хийнэ."""
        rows = [
            {
                "user_id":          user_id,
                "run_id":           run_id,
                "rule_id":          d["rule_id"],
                "pattern_type":     d["pattern_type"],
                "pattern_data":     d["pattern_data"],
                "strength_score":   d["strength_score"],
                "related_node_ids": d.get("related_node_ids") or [],
            }
            for d in detected
        ]
        self._db.table("detected_patterns").insert(rows).execute()

    def _finish_run(self, run_id: str, status: str = "completed") -> None:
        self._db.table("pattern_runs").update(
            {
                "run_finished_at": datetime.now(timezone.utc).isoformat(),
                "status":          status,
            }
        ).eq("id", run_id).execute()

    # ── Builder ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_result(
        rule: dict,
        pattern_data: dict,
        strength: float,
        node_ids: list[str] | None = None,
    ) -> dict:
        return {
            "rule_id":          rule["id"],
            "pattern_type":     rule["rule_name"],
            "pattern_data":     pattern_data,
            "strength_score":   round(min(max(strength, 0.0), 1.0), 4),
            "related_node_ids": node_ids or [],
        }