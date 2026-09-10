from __future__ import annotations

"""Rank existing Raid Review findings into a small actionable priority list.

This service does not create combat truth, change finding priority, or infer causation.
It is a presentation/decision layer over findings that have already been produced by
reviewed analysis services. The complete findings remain authoritative and available.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_service import RaidReviewFinding


_PRIORITY_ORDER = {"high": 0, "medium": 1, "note": 2}
_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}

# When two findings cover the same subject/theme, prefer the finding that already
# joins multiple reviewed evidence streams over the narrower raw comparison.
_CATEGORY_SPECIFICITY = {
    "damage_context": 0,
    "mechanic_window": 0,
    "death_window": 0,
    "survival": 1,
    "landing_recovery_completion": 1,
    "recovery_completion": 1,
    "landing_recovery": 1,
    "boss_contact": 1,
    "healer_effect_coverage": 1,
    "tank_effect_continuity": 1,
    "coverage": 1,
    "sustain": 1,
    "uptime": 2,
    "damage": 3,
}

_CATEGORY_THEME = {
    "death_window": "survival_mechanics",
    "mechanic_window": "survival_mechanics",
    "survival": "survival_mechanics",
    "damage_context": "damage_execution",
    "damage": "damage_execution",
    "boss_contact": "damage_execution",
    "landing_recovery_completion": "landing_execution",
    "recovery_completion": "landing_execution",
    "landing_recovery": "landing_execution",
    "healer_effect_coverage": "support_coverage",
    "tank_effect_continuity": "support_control",
    "coverage": "support_coverage",
    "uptime": "support_coverage",
    "sustain": "sustain",
}


@dataclass(frozen=True, slots=True)
class RaidReviewPriorityItem:
    rank: int
    scope: str
    subject: str
    role: str
    category: str
    priority: str
    title: str
    evidence: str
    recommendation: str
    confidence: str


class PerformanceRaidReviewPriorityService:
    """Select a deterministic, non-destructive shortlist from existing findings."""

    def rank(
        self,
        findings: Iterable[RaidReviewFinding],
        *,
        limit: int = 3,
        include_notes: bool = False,
    ) -> tuple[RaidReviewPriorityItem, ...]:
        requested_limit = max(0, int(limit))
        if requested_limit == 0:
            return ()

        candidates = tuple(
            item
            for item in findings
            if include_notes or str(item.priority).strip().casefold() != "note"
        )
        if not candidates:
            return ()

        selected_by_key: dict[tuple[str, str], RaidReviewFinding] = {}
        for finding in candidates:
            key = (
                str(finding.subject or "").strip().casefold(),
                self._theme(finding.category),
            )
            existing = selected_by_key.get(key)
            if existing is None or self._sort_key(finding) < self._sort_key(existing):
                selected_by_key[key] = finding

        ordered = sorted(selected_by_key.values(), key=self._sort_key)
        return tuple(
            RaidReviewPriorityItem(
                rank=index,
                scope=finding.scope,
                subject=finding.subject,
                role=finding.role,
                category=finding.category,
                priority=finding.priority,
                title=finding.title,
                evidence=finding.evidence,
                recommendation=finding.recommendation,
                confidence=finding.confidence,
            )
            for index, finding in enumerate(ordered[:requested_limit], start=1)
        )

    @staticmethod
    def _theme(category: str) -> str:
        normalized = str(category or "").strip().casefold()
        return _CATEGORY_THEME.get(normalized, normalized or "uncategorized")

    @staticmethod
    def _sort_key(finding: RaidReviewFinding) -> tuple:
        priority = str(finding.priority or "").strip().casefold()
        confidence = str(finding.confidence or "").strip().casefold()
        category = str(finding.category or "").strip().casefold()
        scope = str(finding.scope or "").strip().casefold()
        return (
            _PRIORITY_ORDER.get(priority, 9),
            _CONFIDENCE_ORDER.get(confidence, 9),
            _CATEGORY_SPECIFICITY.get(category, 5),
            0 if scope == "raid" else 1,
            str(finding.subject or "").casefold(),
            str(finding.title or "").casefold(),
        )


__all__ = [
    "PerformanceRaidReviewPriorityService",
    "RaidReviewPriorityItem",
]
