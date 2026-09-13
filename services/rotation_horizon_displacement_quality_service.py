from __future__ import annotations

"""Classify fixed-horizon displacement spillover without mutating the schedule.

The duration scheduler reports any queued skill left beyond the sampled plan horizon.
That raw diagnostic is useful provenance but not, by itself, evidence of a cadence bug.
This service distinguishes proven ordinary-priority starvation from spillover that is
explained by protected or higher-priority same-bar work, late-window truncation, or
insufficient provenance.

Skill-name-level horizon messages are not action-instance identities. A skill can be
cast again while another queued instance with the same name remains displaced. For
that reason, ordinary cadence debt is proven only when the shared priority displacement
audit finds an actual lower-priority ordinary survivor after the displacement start.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_priority_displacement_audit_service import (
    RotationPriorityDisplacementAudit,
    RotationPriorityDisplacementAuditService,
    RotationPriorityHorizonDisplacement,
)


class RotationHorizonDisplacementQuality(str, Enum):
    PROTECTED_OBLIGATION_SATURATION = "protected_obligation_saturation"
    ORDINARY_CADENCE_DEBT = "ordinary_cadence_debt"
    LATE_WINDOW_TRUNCATION = "late_window_truncation"
    UNKNOWN_PROVENANCE = "unknown_provenance"


@dataclass(frozen=True)
class RotationHorizonDisplacementQualityRow:
    bar: str
    skill_name: str
    priority: int
    displaced_from_time_seconds: float | None
    quality: RotationHorizonDisplacementQuality
    later_same_bar_skill_times: tuple[float, ...] = ()
    later_ordinary_skill_times: tuple[float, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class RotationHorizonDisplacementQualityReport:
    rows: tuple[RotationHorizonDisplacementQualityRow, ...]

    @property
    def cadence_debt(self) -> tuple[RotationHorizonDisplacementQualityRow, ...]:
        return tuple(
            row
            for row in self.rows
            if row.quality is RotationHorizonDisplacementQuality.ORDINARY_CADENCE_DEBT
        )

    @property
    def clean_of_proven_cadence_debt(self) -> bool:
        return not self.cadence_debt


class RotationHorizonDisplacementQualityService:
    """Classify horizon spillover using shared priority/provenance evidence."""

    def __init__(
        self,
        *,
        priority_audit: RotationPriorityDisplacementAuditService | None = None,
    ) -> None:
        self.priority_audit = priority_audit or RotationPriorityDisplacementAuditService()

    def classify(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList,
    ) -> RotationHorizonDisplacementQualityReport:
        audit = self.priority_audit.audit(plan, priorities=priorities)
        refresh_claims = self.priority_audit._refresh_claim_times(plan)
        first_cast = self._first_cast_times(plan)
        rows = tuple(
            self._classify_one(
                plan,
                displacement=row,
                audit=audit,
                refresh_claims=refresh_claims,
                first_cast=first_cast,
            )
            for row in audit.displaced_beyond_horizon
        )
        return RotationHorizonDisplacementQualityReport(rows=rows)

    def _classify_one(
        self,
        plan: RotationPlan,
        *,
        displacement: RotationPriorityHorizonDisplacement,
        audit: RotationPriorityDisplacementAudit,
        refresh_claims: dict[tuple[str, str], set[float]],
        first_cast: dict[tuple[str, str], float],
    ) -> RotationHorizonDisplacementQualityRow:
        start = displacement.displaced_from_time_seconds
        if start is None:
            return RotationHorizonDisplacementQualityRow(
                bar=displacement.bar,
                skill_name=displacement.skill_name,
                priority=displacement.priority,
                displaced_from_time_seconds=None,
                quality=RotationHorizonDisplacementQuality.UNKNOWN_PROVENANCE,
                reason="displacement start time is unresolved",
            )

        later = tuple(
            sorted(
                float(action.time_seconds)
                for action in plan.actions
                if action.kind is RotationActionKind.SKILL
                and action.name
                and action.bar == displacement.bar
                and float(action.time_seconds) > float(start)
            )
        )
        ordinary: list[float] = []
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            if action.bar != displacement.bar or float(action.time_seconds) <= float(start):
                continue
            key = (action.name.casefold(), displacement.bar)
            time_seconds = float(action.time_seconds)
            if time_seconds in refresh_claims.get(key, set()):
                continue
            if first_cast.get(key) == time_seconds:
                continue
            ordinary.append(time_seconds)
        ordinary_times = tuple(sorted(ordinary))

        ordinary_inversions = tuple(
            row
            for row in audit.ordinary_inversions
            if row.bar == displacement.bar
            and row.displaced_skill_name.casefold()
            == displacement.skill_name.casefold()
            and abs(
                float(row.displaced_from_time_seconds) - float(start)
            )
            <= 1e-9
        )
        if ordinary_inversions:
            proven_times = tuple(
                sorted(
                    {
                        float(row.lower_priority_last_time_seconds)
                        for row in ordinary_inversions
                    }
                )
            )
            return RotationHorizonDisplacementQualityRow(
                bar=displacement.bar,
                skill_name=displacement.skill_name,
                priority=displacement.priority,
                displaced_from_time_seconds=float(start),
                quality=RotationHorizonDisplacementQuality.ORDINARY_CADENCE_DEBT,
                later_same_bar_skill_times=later,
                later_ordinary_skill_times=proven_times,
                reason=(
                    "a lower-priority ordinary same-bar cast survived after the "
                    "displacement start while the higher-priority skill still spilled "
                    "beyond the horizon"
                ),
            )

        if later:
            return RotationHorizonDisplacementQualityRow(
                bar=displacement.bar,
                skill_name=displacement.skill_name,
                priority=displacement.priority,
                displaced_from_time_seconds=float(start),
                quality=RotationHorizonDisplacementQuality.PROTECTED_OBLIGATION_SATURATION,
                later_same_bar_skill_times=later,
                later_ordinary_skill_times=ordinary_times,
                reason=(
                    "later same-bar work did not contain a proven lower-priority ordinary "
                    "survivor; refresh/first-cast obligations, higher/equal-priority work, "
                    "or same-skill instance ambiguity explain the observed horizon tail"
                ),
            )

        return RotationHorizonDisplacementQualityRow(
            bar=displacement.bar,
            skill_name=displacement.skill_name,
            priority=displacement.priority,
            displaced_from_time_seconds=float(start),
            quality=RotationHorizonDisplacementQuality.LATE_WINDOW_TRUNCATION,
            reason="no later same-bar skill slot existed inside the sampled horizon",
        )

    @staticmethod
    def _first_cast_times(plan: RotationPlan) -> dict[tuple[str, str], float]:
        result: dict[tuple[str, str], float] = {}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            bar = str(action.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                continue
            key = (action.name.casefold(), bar)
            time_seconds = float(action.time_seconds)
            result[key] = min(result.get(key, time_seconds), time_seconds)
        return result


__all__ = [
    "RotationHorizonDisplacementQuality",
    "RotationHorizonDisplacementQualityReport",
    "RotationHorizonDisplacementQualityRow",
    "RotationHorizonDisplacementQualityService",
]
