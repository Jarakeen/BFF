from __future__ import annotations

"""Resolve target-health conditional damage components at exact runtime state.

This service owns no damage formula. It decides only whether one damage component
may contribute its ordinary canonical magnitude for a supplied runtime snapshot.

Exact threshold-gated activation is supported. Continuous ``up to N% more damage``
amplification remains unresolved because Phase 6 records the maximum consequence
but does not define runtime interpolation across target Health.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.combat_state_snapshot import CombatStateSnapshot
from minmax.skill_component_condition import SkillComponentConditionType
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)


class RotationExecuteComponentDamageStatus(str, Enum):
    INCLUDE = "include"
    SUPPRESS = "suppress"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RotationExecuteComponentDamageEligibility:
    status: RotationExecuteComponentDamageStatus
    unresolved: tuple[str, ...] = ()

    @property
    def include(self) -> bool:
        return self.status is RotationExecuteComponentDamageStatus.INCLUDE


class RotationExecuteComponentDamageEligibilityService:
    """Evaluate reviewed target-health consequences without inventing scaling."""

    def resolve(
        self,
        *,
        skill_name: str,
        coefficient_number: int,
        consequences: tuple[SkillComponentConditionalConsequence, ...],
        snapshot: CombatStateSnapshot | None,
        target_identity: str,
    ) -> RotationExecuteComponentDamageEligibility:
        supported = tuple(
            consequence
            for consequence in consequences
            if consequence.condition.condition_type
            is SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT
        )
        if not supported:
            return RotationExecuteComponentDamageEligibility(
                status=RotationExecuteComponentDamageStatus.INCLUDE,
            )

        target = str(target_identity or "").strip()
        if snapshot is None:
            return self._unknown(
                skill_name,
                coefficient_number,
                "target-health conditional damage requires an exact runtime snapshot",
            )
        if not target:
            return self._unknown(
                skill_name,
                coefficient_number,
                "target-health conditional damage requires a target identity",
            )
        target_snapshot = snapshot.target(target)
        if target_snapshot is None:
            return self._unknown(
                skill_name,
                coefficient_number,
                f"runtime target {target!r} is absent from snapshot",
            )
        if target_snapshot.health_fraction() is None:
            return self._unknown(
                skill_name,
                coefficient_number,
                f"runtime target {target!r} Health is unknown",
            )

        active_activation = False
        for consequence in supported:
            condition = consequence.condition
            state = snapshot.meets_health_threshold(
                float(condition.threshold),
                target=target,
            )
            if state is None:
                return self._unknown(
                    skill_name,
                    coefficient_number,
                    f"runtime target {target!r} threshold state is unknown",
                )

            if consequence.consequence_type is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE:
                if state:
                    return self._unknown(
                        skill_name,
                        coefficient_number,
                        "target-health damage amplification is active but exact interpolation is unresolved",
                    )
                # The amplification is inactive above threshold. The ordinary base
                # component still exists and is therefore included normally.
                continue

            if consequence.consequence_type is SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT:
                if state:
                    active_activation = True
                continue

        activations = tuple(
            consequence
            for consequence in supported
            if consequence.consequence_type
            is SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT
        )
        if activations and not active_activation:
            return RotationExecuteComponentDamageEligibility(
                status=RotationExecuteComponentDamageStatus.SUPPRESS,
            )

        return RotationExecuteComponentDamageEligibility(
            status=RotationExecuteComponentDamageStatus.INCLUDE,
        )

    @staticmethod
    def _unknown(
        skill_name: str,
        coefficient_number: int,
        reason: str,
    ) -> RotationExecuteComponentDamageEligibility:
        return RotationExecuteComponentDamageEligibility(
            status=RotationExecuteComponentDamageStatus.UNKNOWN,
            unresolved=(
                f"{skill_name}: coefficient {int(coefficient_number)}: {reason}",
            ),
        )


__all__ = [
    "RotationExecuteComponentDamageEligibility",
    "RotationExecuteComponentDamageEligibilityService",
    "RotationExecuteComponentDamageStatus",
]
