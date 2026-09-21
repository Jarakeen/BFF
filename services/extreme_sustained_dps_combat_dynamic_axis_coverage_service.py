from __future__ import annotations

"""Promote finite skill/rotation/policy frontier closure into canonical axis coverage."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_execute_policy_frontier_service import (
    ExtremeSustainedDPSExecutePolicyFrontier,
)
from services.extreme_sustained_dps_heavy_attack_policy_frontier_service import (
    ExtremeSustainedDPSHeavyAttackPolicyFrontier,
)
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationFamilyFrontier,
)
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSRotationPolicyFrontier,
)
from services.extreme_sustained_dps_skill_bar_frontier_service import (
    ExtremeSustainedDPSSkillBarFrontier,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSCombatDynamicAxisCoverageResult:
    proof: ExtremeSustainedDPSAxisCoverageProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    omitted_scope: tuple[str, ...] = ()


class ExtremeSustainedDPSCombatDynamicAxisCoverageService:
    """Promote only finite dynamic denominator closure actually proven by each frontier."""

    @classmethod
    def skill_bars(
        cls,
        frontier: ExtremeSustainedDPSSkillBarFrontier,
    ) -> ExtremeSustainedDPSCombatDynamicAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS legal skill-bar denominator",
            dominated_axes=("skill_bars",) if complete else (),
            unresolved=unresolved,
        )
        return ExtremeSustainedDPSCombatDynamicAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Front legal skill-bar states: {frontier.front_candidate_count}",
                f"Back legal skill-bar states: {frontier.back_candidate_count}",
                f"Two-bar skill denominator: {frontier.candidate_count}",
                (
                    "Canonical coverage promoted: skill_bars"
                    if complete
                    else "Canonical skill-bar coverage withheld"
                ),
            ),
            unresolved=unresolved,
        )

    @classmethod
    def rotation_seed_family(
        cls,
        frontier: ExtremeSustainedDPSRotationFamilyFrontier,
    ) -> ExtremeSustainedDPSCombatDynamicAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS semi-static seed rotation denominator",
            dominated_axes=(
                ("rotation_order", "light_attack_weave")
                if complete
                else ()
            ),
            unresolved=unresolved,
        )
        omitted = (
            "starting-bar route remains part of rotation-order family identity",
            "Ultimate timing/potion timing/execute/Heavy Attack/encounter-demand policies remain separate",
        )
        return ExtremeSustainedDPSCombatDynamicAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Rotation seed candidates: {frontier.candidate_count}",
                f"Front skill orderings: {frontier.front_order_count}",
                f"Back skill orderings: {frontier.back_order_count}",
                f"Starting routes: {frontier.starting_route_count}",
                f"Light-Attack weave states: {frontier.weave_state_count}",
                (
                    "Canonical coverage promoted: rotation_order + light_attack_weave"
                    if complete
                    else "Canonical seed-rotation coverage withheld"
                ),
            ),
            unresolved=unresolved,
            omitted_scope=omitted,
        )

    @classmethod
    def anchored_ultimate_potion_policy(
        cls,
        frontier: ExtremeSustainedDPSRotationPolicyFrontier,
    ) -> ExtremeSustainedDPSCombatDynamicAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(
            frontier.anchored_policy_denominator_proven
            and not unresolved
        )
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete anchored Ultimate/potion policy denominator",
            dominated_axes=(
                ("ultimate_policy", "potion_timing_policy")
                if complete
                else ()
            ),
            unresolved=unresolved,
        )

        omitted: list[str] = []
        if not frontier.continuous_potion_timing_closed:
            omitted.append(
                "continuous potion first-use offset is not closed by anchored policy coverage"
            )
        if not frontier.delayed_ultimate_timing_closed:
            omitted.append(
                "deliberate post-affordability Ultimate delay is not closed by anchored policy coverage"
            )

        return ExtremeSustainedDPSCombatDynamicAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Anchored Ultimate/potion policy candidates: {frontier.candidate_count}",
                f"Ultimate choices: {len(frontier.ultimate_options)}",
                f"Anchored potion policies: {len(frontier.potion_policies)}",
                (
                    "Canonical anchored-family coverage promoted: ultimate_policy + potion_timing_policy"
                    if complete
                    else "Canonical anchored Ultimate/potion coverage withheld"
                ),
                "This coverage is finite anchored-family closure only, not theoretical continuous timing closure",
            ),
            unresolved=unresolved,
            omitted_scope=tuple(omitted),
        )

    @classmethod
    def execute_policy(
        cls,
        frontier: ExtremeSustainedDPSExecutePolicyFrontier,
    ) -> ExtremeSustainedDPSCombatDynamicAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS execute-policy denominator",
            dominated_axes=("execute_policy",) if complete else (),
            unresolved=unresolved,
        )
        return ExtremeSustainedDPSCombatDynamicAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Execute policy variants retained: {len(frontier.candidates)}",
                (
                    "Canonical coverage promoted: execute_policy"
                    if complete
                    else "Canonical execute-policy coverage withheld"
                ),
            ),
            unresolved=unresolved,
        )

    @classmethod
    def heavy_attack_policy(
        cls,
        frontier: ExtremeSustainedDPSHeavyAttackPolicyFrontier,
    ) -> ExtremeSustainedDPSCombatDynamicAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete reviewed Heavy Attack policy denominator",
            dominated_axes=("heavy_attack_policy",) if complete else (),
            unresolved=unresolved,
        )
        return ExtremeSustainedDPSCombatDynamicAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Heavy Attack policy variants retained: {len(frontier.candidates)}",
                (
                    "Canonical coverage promoted: heavy_attack_policy"
                    if complete
                    else "Canonical Heavy Attack policy coverage withheld"
                ),
                "Coverage applies only to caller-supplied reviewed safe Heavy Attack windows",
            ),
            unresolved=unresolved,
            omitted_scope=(
                "Heavy Attack windows outside the caller-supplied reviewed safe set are not claimed closed",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSCombatDynamicAxisCoverageResult",
    "ExtremeSustainedDPSCombatDynamicAxisCoverageService",
]
