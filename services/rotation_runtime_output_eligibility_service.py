from __future__ import annotations

"""Canonical rotation bridge for fail-closed conditional combat output."""

from dataclasses import dataclass

from minmax.character_build.effect_relationship import ConditionContext
from minmax.runtime_output_eligibility import (
    RuntimeOutputEligibilityResult,
    RuntimeOutputEligibilityRule,
    evaluate_runtime_output_eligibility,
)
from minmax.skill_coefficient_repository import ability_entity_id


DETONATING_SIPHON_GEOMETRY_CONDITION = "target_in_detonating_siphon_geometry"


@dataclass(frozen=True)
class RotationRuntimeOutputConditionRule:
    skill_entity_id: str
    coefficient_number: int
    eligibility: RuntimeOutputEligibilityRule

    def __post_init__(self) -> None:
        identity = ability_entity_id(self.skill_entity_id)
        if not identity:
            raise ValueError("rotation output eligibility rule requires canonical skill identity")
        object.__setattr__(self, "skill_entity_id", identity)
        if self.coefficient_number <= 0:
            raise ValueError("rotation output eligibility coefficient_number must be positive")


@dataclass(frozen=True)
class RotationRuntimeOutputEligibilityResult:
    skill_entity_id: str
    coefficient_number: int
    has_rule: bool
    eligible: bool
    resolved: bool
    required_conditions: tuple[str, ...] = ()
    missing_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


_REVIEWED_RULES: tuple[RotationRuntimeOutputConditionRule, ...] = (
    RotationRuntimeOutputConditionRule(
        skill_entity_id="detonating_siphon",
        coefficient_number=1,
        eligibility=RuntimeOutputEligibilityRule(
            required_conditions=(DETONATING_SIPHON_GEOMETRY_CONDITION,),
            source=(
                "reviewed Detonating Siphon tooltip geometry: enemies around the corpse "
                "and between the caster and corpse"
            ),
        ),
    ),
)


class RotationRuntimeOutputEligibilityService:
    """Evaluate reviewed skill-component output conditions without inventing runtime state.

    Rules are keyed by canonical skill identity plus coefficient number. Skills/components
    with no reviewed rule pass through unchanged. A reviewed conditional output fails closed
    when no ``ConditionContext`` is supplied. A supplied context that does not contain every
    required opaque condition resolves deterministically to ineligible output.

    Detonating Siphon is intentionally represented only as an opaque geometry requirement.
    This service does not calculate corpse position, player position, target position, radius,
    line geometry, cadence, or tick timing. Until a caller can prove the named condition at
    the exact output instant, Siphon damage remains unresolved rather than guessed.
    """

    def __init__(
        self,
        rules: tuple[RotationRuntimeOutputConditionRule, ...] = _REVIEWED_RULES,
    ) -> None:
        keyed: dict[tuple[str, int], RotationRuntimeOutputConditionRule] = {}
        for rule in rules:
            key = (rule.skill_entity_id, rule.coefficient_number)
            if key in keyed:
                raise ValueError(
                    "duplicate rotation output eligibility rule for "
                    f"{rule.skill_entity_id} coefficient {rule.coefficient_number}"
                )
            keyed[key] = rule
        self._rules = keyed

    def rule_for(
        self,
        skill_entity_id: str,
        coefficient_number: int,
    ) -> RotationRuntimeOutputConditionRule | None:
        return self._rules.get(
            (ability_entity_id(skill_entity_id), int(coefficient_number))
        )

    def evaluate(
        self,
        *,
        skill_entity_id: str,
        coefficient_number: int,
        condition_context: ConditionContext | None,
    ) -> RotationRuntimeOutputEligibilityResult:
        identity = ability_entity_id(skill_entity_id)
        number = int(coefficient_number)
        rule = self.rule_for(identity, number)
        if rule is None:
            return RotationRuntimeOutputEligibilityResult(
                skill_entity_id=identity,
                coefficient_number=number,
                has_rule=False,
                eligible=True,
                resolved=True,
            )

        result: RuntimeOutputEligibilityResult = evaluate_runtime_output_eligibility(
            rule.eligibility,
            condition_context,
        )
        evidence = (
            "required runtime output conditions: "
            + ", ".join(rule.eligibility.required_conditions),
            f"condition provenance: {rule.eligibility.source}",
        )
        unresolved: tuple[str, ...] = ()
        if not result.resolved:
            unresolved = (
                f"{identity} coefficient {number}: runtime output eligibility requires "
                "authoritative ConditionContext for "
                + ", ".join(result.missing_conditions),
            )

        return RotationRuntimeOutputEligibilityResult(
            skill_entity_id=identity,
            coefficient_number=number,
            has_rule=True,
            eligible=result.eligible,
            resolved=result.resolved,
            required_conditions=rule.eligibility.required_conditions,
            missing_conditions=result.missing_conditions,
            evidence=evidence,
            unresolved=unresolved,
        )


__all__ = [
    "DETONATING_SIPHON_GEOMETRY_CONDITION",
    "RotationRuntimeOutputConditionRule",
    "RotationRuntimeOutputEligibilityResult",
    "RotationRuntimeOutputEligibilityService",
]
