from __future__ import annotations

"""Enrich horizon-displacement quality with replayed queue-instance provenance.

The base horizon-quality service remains the owner of cadence-debt judgment.  This
adapter only replaces ``unknown_provenance`` when diagnostic replay proves that the
production horizon message collapsed multiple concrete same-skill action instances
that survived in the final displacement queue.

A deduplicated queue tail is provenance evidence, not proof that the schedule is good
or bad.  Ordinary cadence debt remains owned exclusively by the shared priority audit.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from services.rotation_horizon_displacement_quality_service import (
    RotationHorizonDisplacementQuality,
    RotationHorizonDisplacementQualityService,
)
from services.rotation_priority_displacement_provenance_replay_service import (
    RotationDisplacementQueueInstance,
    RotationDisplacementSpilloverProvenance,
)


class RotationHorizonDisplacementProvenanceQuality(str, Enum):
    PROTECTED_OBLIGATION_SATURATION = "protected_obligation_saturation"
    ORDINARY_CADENCE_DEBT = "ordinary_cadence_debt"
    LATE_WINDOW_TRUNCATION = "late_window_truncation"
    DEDUPLICATED_QUEUE_SATURATION = "deduplicated_queue_saturation"
    UNKNOWN_PROVENANCE = "unknown_provenance"


@dataclass(frozen=True)
class RotationHorizonDisplacementProvenanceQualityRow:
    bar: str
    skill_name: str
    priority: int
    displaced_from_time_seconds: float | None
    quality: RotationHorizonDisplacementProvenanceQuality
    later_same_bar_skill_times: tuple[float, ...] = ()
    later_ordinary_skill_times: tuple[float, ...] = ()
    plausible_instances: tuple[RotationDisplacementQueueInstance, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class RotationHorizonDisplacementProvenanceQualityReport:
    rows: tuple[RotationHorizonDisplacementProvenanceQualityRow, ...]

    @property
    def cadence_debt(self) -> tuple[RotationHorizonDisplacementProvenanceQualityRow, ...]:
        return tuple(
            row
            for row in self.rows
            if row.quality
            is RotationHorizonDisplacementProvenanceQuality.ORDINARY_CADENCE_DEBT
        )

    @property
    def clean_of_proven_cadence_debt(self) -> bool:
        return not self.cadence_debt


class RotationHorizonDisplacementProvenanceQualityService:
    """Compose base horizon quality with exact diagnostic replay provenance."""

    def __init__(
        self,
        *,
        base: RotationHorizonDisplacementQualityService | None = None,
    ) -> None:
        self.base = base or RotationHorizonDisplacementQualityService()

    def classify(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList,
        spillover_provenance: tuple[
            RotationDisplacementSpilloverProvenance, ...
        ] = (),
    ) -> RotationHorizonDisplacementProvenanceQualityReport:
        base_report = self.base.classify(plan, priorities=priorities)
        provenance_by_key = {
            (item.skill_name.casefold(), item.bar): item
            for item in spillover_provenance
        }
        rows: list[RotationHorizonDisplacementProvenanceQualityRow] = []
        for row in base_report.rows:
            key = (row.skill_name.casefold(), row.bar)
            provenance = provenance_by_key.get(key)
            if (
                row.quality is RotationHorizonDisplacementQuality.UNKNOWN_PROVENANCE
                and provenance is not None
                and len(provenance.plausible_instances) > 1
            ):
                rows.append(
                    RotationHorizonDisplacementProvenanceQualityRow(
                        bar=row.bar,
                        skill_name=row.skill_name,
                        priority=row.priority,
                        displaced_from_time_seconds=row.displaced_from_time_seconds,
                        quality=(
                            RotationHorizonDisplacementProvenanceQuality.DEDUPLICATED_QUEUE_SATURATION
                        ),
                        later_same_bar_skill_times=row.later_same_bar_skill_times,
                        later_ordinary_skill_times=row.later_ordinary_skill_times,
                        plausible_instances=provenance.plausible_instances,
                        reason=(
                            "diagnostic replay proves multiple concrete same-skill action "
                            "instances survive in the final displacement queue; production "
                            "deduplicates their identical horizon messages, so one unique "
                            "source instance cannot be named. This is provenance evidence, "
                            "not proof of ordinary cadence debt"
                        ),
                    )
                )
                continue

            rows.append(
                RotationHorizonDisplacementProvenanceQualityRow(
                    bar=row.bar,
                    skill_name=row.skill_name,
                    priority=row.priority,
                    displaced_from_time_seconds=row.displaced_from_time_seconds,
                    quality=RotationHorizonDisplacementProvenanceQuality(row.quality.value),
                    later_same_bar_skill_times=row.later_same_bar_skill_times,
                    later_ordinary_skill_times=row.later_ordinary_skill_times,
                    plausible_instances=(
                        provenance.plausible_instances if provenance is not None else ()
                    ),
                    reason=row.reason,
                )
            )

        return RotationHorizonDisplacementProvenanceQualityReport(rows=tuple(rows))


__all__ = [
    "RotationHorizonDisplacementProvenanceQuality",
    "RotationHorizonDisplacementProvenanceQualityReport",
    "RotationHorizonDisplacementProvenanceQualityRow",
    "RotationHorizonDisplacementProvenanceQualityService",
]
