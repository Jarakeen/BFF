from __future__ import annotations

"""Resolve target-health conditional damage components at exact runtime state.

This service owns no base damage formula. It decides whether one damage component
may contribute and, when source-reviewed execute interpolation exists, exposes the
resulting damage multiplier.

Exact threshold-gated activation is supported. Continuous ``up to N% more damage``
remains unresolved unless a reviewed skill-specific interpolation semantic exists.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.combat_state_snapshot import CombatStateSnapshot
from minmax.skill_component_condition import SkillComponentConditionType
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from services.rotation_reviewed_execute_amplification_service import (
    RotationReviewedExecuteAmplificationService,
)


class RotationExecuteComponentDamageStatus(str, Enum):
    INCLUDE = "include"
    SUPPRESS = "suppress"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RotationExecuteComponentDamageEligibility:
    status: RotationExecuteComponentDamageStatus
    damage_multiplier: float = 1.0
    unresolved: tuple[str, ...] = ()

    @property
    def include(self) -> bool:
        return self.status is RotationExecuteComponentDamageStatus.INCLUDE


class RotationExecuteComponentDamageEligibilityService:
    """Evaluate reviewed target-health consequences without inventing scaling."""

    def __init__(
        self,
        *,
        amplification: RotationReviewedExecuteAmplificationService | None = None,
    ) -> None:
        self.amplification = amplification or RotationReviewedExecuteAmplificationService()

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
        health_fraction = target_snapshot.health_fraction()
        if health_fraction is None:
            return self._unknown(
                skill_name,
                coefficient_number,
                f"runtime target {target!r} Health is unknown",
            )

        active_activation = False
        damage_multiplier = 1.0
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
                if not state:
                    continue
                amplification = self.amplification.resolve_multiplier(
                    skill_name=skill_name,
                    health_fraction=float(health_fraction),
                    threshold=float(condition.threshold),
                    maximum_bonus_fraction=consequence.maximum_bonus_fraction,
                )
                if not amplification.resolved or amplification.damage_multiplier is None:
                    detail = tuple(amplification.unresolved) or (
                        "target-health damage amplification interpolation is unresolved",
                    )
                    return self._unknown(
                        skill_name,
                        coefficient_number,
                        "; ".join(detail),
                    )
                damage_multiplier *= float(amplification.damage_multiplier)
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
            damage_multiplier=damage_multiplier,
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
