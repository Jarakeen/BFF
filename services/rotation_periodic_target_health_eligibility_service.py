from __future__ import annotations

"""Evaluate target-Health-conditioned periodic damage at reviewed runtime instants."""

from dataclasses import dataclass

from minmax.combat_state_snapshot import CombatStateSnapshot
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_conditional_consequence import SkillComponentConditionalConsequence
from services.rotation_execute_component_damage_eligibility_service import (
    RotationExecuteComponentDamageEligibilityService,
    RotationExecuteComponentDamageStatus,
)
from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
    RotationPeriodicTargetHealthSemanticsService,
)


@dataclass(frozen=True)
class RotationPeriodicTargetHealthOccurrenceEligibility:
    time_seconds: float
    include: bool
    damage_multiplier: float = 1.0
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationPeriodicTargetHealthEligibilityResult:
    occurrences: tuple[RotationPeriodicTargetHealthOccurrenceEligibility, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved and all(not row.unresolved for row in self.occurrences)


class RotationPeriodicTargetHealthEligibilityService:
    """Apply reviewed cast-snapshot or per-tick target-Health policy to DoT ticks."""

    def __init__(
        self,
        *,
        semantics_service: RotationPeriodicTargetHealthSemanticsService,
        execute_eligibility_service: RotationExecuteComponentDamageEligibilityService | None = None,
    ) -> None:
        self.semantics_service = semantics_service
        self.execute_eligibility_service = (
            execute_eligibility_service or RotationExecuteComponentDamageEligibilityService()
        )

    def evaluate(
        self,
        *,
        skill_name: str,
        coefficient_number: int,
        consequences: tuple[SkillComponentConditionalConsequence, ...],
        runtime_events: tuple[RuntimeEvent, ...],
        cast_time_seconds: float,
        cast_sequence: int | None,
        snapshot_resolver,
        target_identity: str,
    ) -> RotationPeriodicTargetHealthEligibilityResult:
        semantic = self.semantics_service.resolve(
            skill_name=skill_name,
            coefficient_number=coefficient_number,
        )
        if semantic is None:
            reason = (
                f"{skill_name}: coefficient {int(coefficient_number)} periodic target-Health timing is not source-reviewed"
            )
            return RotationPeriodicTargetHealthEligibilityResult(
                occurrences=(),
                unresolved=(reason,),
            )

        if semantic.policy is PeriodicTargetHealthTimingPolicy.SNAPSHOT_AT_CAST:
            snapshot = snapshot_resolver(float(cast_time_seconds), cast_sequence)
            eligibility = self.execute_eligibility_service.resolve(
                skill_name=skill_name,
                coefficient_number=coefficient_number,
                consequences=consequences,
                snapshot=snapshot,
                target_identity=target_identity,
            )
            if eligibility.status is RotationExecuteComponentDamageStatus.UNKNOWN:
                return RotationPeriodicTargetHealthEligibilityResult(
                    occurrences=(),
                    unresolved=tuple(eligibility.unresolved),
                )
            include = eligibility.status is RotationExecuteComponentDamageStatus.INCLUDE
            return RotationPeriodicTargetHealthEligibilityResult(
                occurrences=tuple(
                    RotationPeriodicTargetHealthOccurrenceEligibility(
                        time_seconds=float(event.time_seconds),
                        include=include,
                        damage_multiplier=float(eligibility.damage_multiplier),
                    )
                    for event in runtime_events
                ),
            )

        if semantic.policy is PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK:
            rows: list[RotationPeriodicTargetHealthOccurrenceEligibility] = []
            unresolved: list[str] = []
            for event in runtime_events:
                snapshot: CombatStateSnapshot | None = snapshot_resolver(
                    float(event.time_seconds),
                    None,
                )
                eligibility = self.execute_eligibility_service.resolve(
                    skill_name=skill_name,
                    coefficient_number=coefficient_number,
                    consequences=consequences,
                    snapshot=snapshot,
                    target_identity=target_identity,
                )
                if eligibility.status is RotationExecuteComponentDamageStatus.UNKNOWN:
                    detail = tuple(eligibility.unresolved) or (
                        "periodic target-Health eligibility is unresolved",
                    )
                    unresolved.extend(
                        f"{skill_name}: coefficient {int(coefficient_number)} tick at {float(event.time_seconds):g}s: {message}"
                        for message in detail
                    )
                    continue
                rows.append(
                    RotationPeriodicTargetHealthOccurrenceEligibility(
                        time_seconds=float(event.time_seconds),
                        include=(eligibility.status is RotationExecuteComponentDamageStatus.INCLUDE),
                        damage_multiplier=float(eligibility.damage_multiplier),
                    )
                )
            return RotationPeriodicTargetHealthEligibilityResult(
                occurrences=tuple(rows),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        return RotationPeriodicTargetHealthEligibilityResult(
            occurrences=(),
            unresolved=(
                f"{skill_name}: coefficient {int(coefficient_number)} periodic target-Health timing policy is unsupported: {semantic.policy}",
            ),
        )


__all__ = [
    "RotationPeriodicTargetHealthEligibilityResult",
    "RotationPeriodicTargetHealthEligibilityService",
    "RotationPeriodicTargetHealthOccurrenceEligibility",
]
