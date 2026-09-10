from __future__ import annotations

"""Presentation-neutral synthesis over already-reviewed Raid Review findings.

This service owns no combat truth and does not reinterpret ESO Logs evidence. It turns
final ``RaidReviewFinding`` rows plus the existing deterministic priority shortlist into
stable sections that a UI can render without duplicating ranking/grouping logic.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_priority_service import RaidReviewPriorityItem
from services.performance_raid_review_service import RaidReviewFinding, RaidReviewReport


_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
_ROLE_ORDER = {"Group": 0, "Healer": 1, "Tank": 2, "DPS": 3}


@dataclass(frozen=True, slots=True)
class RaidReviewRoleFocus:
    role: str
    actionable_count: int
    note_count: int
    categories: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RaidReviewSynthesis:
    encounter_name: str
    pull_count: int
    kill_count: int
    wipe_count: int
    top_priorities: tuple[RaidReviewPriorityItem, ...]
    what_is_working: tuple[RaidReviewFinding, ...]
    role_focus: tuple[RaidReviewRoleFocus, ...]


class PerformanceRaidReviewSynthesisService:
    """Build stable review sections from the final evidence-backed finding set."""

    def synthesize(
        self,
        report: RaidReviewReport,
        priorities: Iterable[RaidReviewPriorityItem],
        *,
        working_limit: int = 3,
    ) -> RaidReviewSynthesis:
        findings = tuple(report.findings)
        priority_rows = tuple(priorities)
        requested_working = max(0, int(working_limit))

        notes = tuple(
            sorted(
                (item for item in findings if self._priority(item) == "note"),
                key=self._working_sort_key,
            )
        )
        working = self._dedupe_notes(notes)[:requested_working]

        role_buckets: dict[str, list[RaidReviewFinding]] = {}
        for finding in findings:
            role = self._canonical_role(finding.role, finding.scope)
            role_buckets.setdefault(role, []).append(finding)

        role_focus: list[RaidReviewRoleFocus] = []
        for role, rows in role_buckets.items():
            actionable = sum(1 for row in rows if self._priority(row) in {"high", "medium"})
            note_count = sum(1 for row in rows if self._priority(row) == "note")
            categories = tuple(
                sorted(
                    {
                        str(row.category or "").strip()
                        for row in rows
                        if str(row.category or "").strip()
                    },
                    key=str.casefold,
                )
            )
            role_focus.append(
                RaidReviewRoleFocus(
                    role=role,
                    actionable_count=actionable,
                    note_count=note_count,
                    categories=categories,
                )
            )

        role_focus.sort(
            key=lambda row: (
                -row.actionable_count,
                _ROLE_ORDER.get(row.role, 9),
                row.role.casefold(),
            )
        )

        return RaidReviewSynthesis(
            encounter_name=report.encounter_name,
            pull_count=int(report.pull_count),
            kill_count=int(report.kill_count),
            wipe_count=int(report.wipe_count),
            top_priorities=priority_rows,
            what_is_working=working,
            role_focus=tuple(role_focus),
        )

    @classmethod
    def _dedupe_notes(
        cls,
        notes: tuple[RaidReviewFinding, ...],
    ) -> tuple[RaidReviewFinding, ...]:
        selected: dict[tuple[str, str], RaidReviewFinding] = {}
        for finding in notes:
            key = (
                str(finding.subject or "").strip().casefold(),
                cls._theme(finding.category),
            )
            selected.setdefault(key, finding)
        return tuple(selected.values())

    @staticmethod
    def _working_sort_key(finding: RaidReviewFinding) -> tuple:
        confidence = str(finding.confidence or "").strip().casefold()
        scope = str(finding.scope or "").strip().casefold()
        role = PerformanceRaidReviewSynthesisService._canonical_role(finding.role, finding.scope)
        return (
            _CONFIDENCE_ORDER.get(confidence, 9),
            0 if scope == "raid" else 1,
            _ROLE_ORDER.get(role, 9),
            str(finding.subject or "").casefold(),
            str(finding.category or "").casefold(),
            str(finding.title or "").casefold(),
        )

    @staticmethod
    def _priority(finding: RaidReviewFinding) -> str:
        return str(finding.priority or "").strip().casefold()

    @staticmethod
    def _canonical_role(role: str, scope: str) -> str:
        if str(scope or "").strip().casefold() == "raid":
            return "Group"
        value = str(role or "").strip().casefold()
        if value in {"healer", "healing"}:
            return "Healer"
        if value in {"tank", "tanking"}:
            return "Tank"
        if value in {"group", "raid"}:
            return "Group"
        return "DPS"

    @staticmethod
    def _theme(category: str) -> str:
        normalized = str(category or "").strip().casefold()
        if normalized in {"damage", "damage_context", "boss_contact"}:
            return "damage_execution"
        if normalized in {"landing_recovery", "landing_recovery_completion", "recovery_completion"}:
            return "landing_execution"
        if normalized in {"healer_effect_coverage", "tank_effect_continuity", "coverage", "uptime"}:
            return "support_coverage"
        if normalized in {"survival", "death_window", "mechanic_window"}:
            return "survival_mechanics"
        return normalized or "uncategorized"


__all__ = [
    "PerformanceRaidReviewSynthesisService",
    "RaidReviewRoleFocus",
    "RaidReviewSynthesis",
]
