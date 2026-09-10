from __future__ import annotations

"""Build stable per-player Raid Review summaries from reviewed findings.

This service is a presentation/decision layer only. It does not reinterpret combat
truth. Player identity comes from ``RaidReviewObservation.stable_member_key`` rather
than display name alone. Findings currently carry presentation labels, so they are
assigned to a stable player only when the label/role pair resolves unambiguously among
the supplied observations. Ambiguous findings remain explicit instead of being guessed.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_service import RaidReviewFinding, RaidReviewObservation


_PRIORITY_ORDER = {"high": 0, "medium": 1, "note": 2}
_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True, slots=True)
class RaidReviewPlayerSummary:
    member_key: str
    actor_label: str
    role: str
    pull_count: int
    kill_count: int
    wipe_count: int
    improvements: tuple[RaidReviewFinding, ...]
    strengths: tuple[RaidReviewFinding, ...]


@dataclass(frozen=True, slots=True)
class RaidReviewPlayerSummaryResult:
    summaries: tuple[RaidReviewPlayerSummary, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewPlayerSummaryService:
    """Produce deterministic per-player strengths and improvement summaries."""

    def summarize(
        self,
        observations: Iterable[RaidReviewObservation],
        findings: Iterable[RaidReviewFinding],
        *,
        improvement_limit: int = 3,
        strength_limit: int = 3,
    ) -> RaidReviewPlayerSummaryResult:
        rows = tuple(observations)
        finding_rows = tuple(findings)
        improvement_cap = max(0, int(improvement_limit))
        strength_cap = max(0, int(strength_limit))

        by_member: dict[str, list[RaidReviewObservation]] = {}
        for row in rows:
            by_member.setdefault(row.stable_member_key, []).append(row)

        label_role_index: dict[tuple[str, str], set[str]] = {}
        for member_key, member_rows in by_member.items():
            for row in member_rows:
                key = (
                    str(row.actor_label or "").strip().casefold(),
                    row.canonical_role.casefold(),
                )
                label_role_index.setdefault(key, set()).add(member_key)

        assigned: dict[str, list[RaidReviewFinding]] = {key: [] for key in by_member}
        unresolved: list[str] = []

        for finding in finding_rows:
            if str(finding.scope or "").strip().casefold() != "player":
                continue
            lookup = (
                str(finding.subject or "").strip().casefold(),
                self._canonical_role(finding.role).casefold(),
            )
            candidates = label_role_index.get(lookup, set())
            if len(candidates) == 1:
                assigned[next(iter(candidates))].append(finding)
                continue
            if not candidates:
                unresolved.append(
                    f"Could not resolve player finding {finding.title!r} for {finding.subject!r} ({finding.role})."
                )
            else:
                unresolved.append(
                    f"Ambiguous player finding {finding.title!r} for {finding.subject!r} ({finding.role}); "
                    f"{len(candidates)} stable players share that display identity."
                )

        summaries: list[RaidReviewPlayerSummary] = []
        for member_key, member_rows in by_member.items():
            sample = member_rows[0]
            member_findings = tuple(assigned.get(member_key, ()))
            improvements = tuple(
                sorted(
                    (item for item in member_findings if self._priority(item) in {"high", "medium"}),
                    key=self._finding_sort_key,
                )
            )
            strengths = tuple(
                sorted(
                    (item for item in member_findings if self._priority(item) == "note"),
                    key=self._finding_sort_key,
                )
            )
            improvements = self._dedupe_by_theme(improvements)[:improvement_cap]
            strengths = self._dedupe_by_theme(strengths)[:strength_cap]

            pull_keys = {(row.report_code, int(row.fight_id)) for row in member_rows}
            kill_keys = {
                (row.report_code, int(row.fight_id))
                for row in member_rows
                if bool(row.kill)
            }
            summaries.append(
                RaidReviewPlayerSummary(
                    member_key=member_key,
                    actor_label=str(sample.actor_label),
                    role=sample.canonical_role,
                    pull_count=len(pull_keys),
                    kill_count=len(kill_keys),
                    wipe_count=len(pull_keys - kill_keys),
                    improvements=improvements,
                    strengths=strengths,
                )
            )

        summaries.sort(key=lambda item: (self._role_order(item.role), item.actor_label.casefold(), item.member_key))
        return RaidReviewPlayerSummaryResult(
            summaries=tuple(summaries),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _dedupe_by_theme(
        cls,
        findings: tuple[RaidReviewFinding, ...],
    ) -> tuple[RaidReviewFinding, ...]:
        selected: dict[str, RaidReviewFinding] = {}
        for finding in findings:
            selected.setdefault(cls._theme(finding.category), finding)
        return tuple(selected.values())

    @staticmethod
    def _finding_sort_key(finding: RaidReviewFinding) -> tuple:
        return (
            _PRIORITY_ORDER.get(str(finding.priority or "").strip().casefold(), 9),
            _CONFIDENCE_ORDER.get(str(finding.confidence or "").strip().casefold(), 9),
            str(finding.category or "").strip().casefold(),
            str(finding.title or "").strip().casefold(),
        )

    @staticmethod
    def _canonical_role(role: str) -> str:
        value = str(role or "").strip().casefold()
        if value in {"healer", "healing"}:
            return "Healer"
        if value in {"tank", "tanking"}:
            return "Tank"
        return "DPS"

    @staticmethod
    def _role_order(role: str) -> int:
        return {"Healer": 0, "Tank": 1, "DPS": 2}.get(role, 9)

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
    "PerformanceRaidReviewPlayerSummaryService",
    "RaidReviewPlayerSummary",
    "RaidReviewPlayerSummaryResult",
]
