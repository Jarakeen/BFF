from __future__ import annotations

"""Lazy indexed adapters for generated dynamic whole-plan dominance families."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_execute_policy_frontier_service import (
    ExtremeSustainedDPSExecutePolicyCandidate,
    ExtremeSustainedDPSExecutePolicyFrontier,
)
from services.extreme_sustained_dps_generated_candidate_assembly_service import (
    ExtremeSustainedDPSAssembledCandidate,
)
from services.extreme_sustained_dps_heavy_attack_policy_frontier_service import (
    ExtremeSustainedDPSHeavyAttackPolicyCandidate,
    ExtremeSustainedDPSHeavyAttackPolicyFrontier,
)
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationPlanCandidate,
    ExtremeSustainedDPSRotationPlanFrontierService,
)
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSRotationPlanCandidate as _UnusedSeedAlias,
    ExtremeSustainedDPSRotationPolicyCandidate,
    ExtremeSustainedDPSRotationPolicyFrontierService,
)
from services.rotation_ultimate_service import HeroismWindow, UltimateGenerationEvent


T = TypeVar("T")


@dataclass(frozen=True)
class ExtremeSustainedDPSIndexedWholePlanAdapter(Generic[T]):
    axes: tuple[str, ...]
    choice_count: int
    denominator_proven: bool
    omitted_scope: tuple[str, ...]
    _resolver: Callable[[int], T]

    def __post_init__(self) -> None:
        count = int(self.choice_count)
        if count < 0:
            raise ValueError("indexed whole-plan adapter choice_count cannot be negative")
        object.__setattr__(self, "choice_count", count)

    def choice_at(self, index: int) -> T:
        target = int(index)
        if target < 0 or target >= self.choice_count:
            raise IndexError("indexed whole-plan adapter choice index out of range")
        return self._resolver(target)


class ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService:
    """Expose dynamic finite families through the whole-plan dominance contract."""

    @classmethod
    def rotation_seed(
        cls,
        frontier_service: ExtremeSustainedDPSRotationPlanFrontierService,
        candidate: ExtremeSustainedDPSAssembledCandidate,
        *,
        duration_seconds: float,
    ) -> ExtremeSustainedDPSIndexedWholePlanAdapter[ExtremeSustainedDPSRotationPlanCandidate]:
        frontier = frontier_service.frontier(candidate)
        return ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("rotation_order", "light_attack_weave"),
            choice_count=int(frontier.candidate_count),
            denominator_proven=bool(frontier.denominator_proven),
            omitted_scope=(
                "starting-bar route remains part of rotation-order family identity",
                "Ultimate/potion/execute/Heavy Attack/encounter-demand policies remain separate",
            ),
            _resolver=lambda index: frontier_service.candidate_at(
                candidate,
                duration_seconds=float(duration_seconds),
                index=index,
            ),
        )

    @classmethod
    def anchored_ultimate_potion(
        cls,
        frontier_service: ExtremeSustainedDPSRotationPolicyFrontierService,
        *,
        build: PlayerBuild,
        seed: ExtremeSustainedDPSRotationPlanCandidate,
        potion_cooldown_seconds: float,
        starting_ultimate: float,
        ultimate_generation_events: tuple[UltimateGenerationEvent, ...] = (),
        heroism_windows: tuple[HeroismWindow, ...] = (),
        use_scheduled_combat_attacks_for_ultimate: bool = False,
    ) -> ExtremeSustainedDPSIndexedWholePlanAdapter[ExtremeSustainedDPSRotationPolicyCandidate]:
        frontier = frontier_service.frontier(
            build=build,
            seed=seed,
            potion_cooldown_seconds=float(potion_cooldown_seconds),
        )
        omitted = []
        if not frontier.continuous_potion_timing_closed:
            omitted.append("continuous potion first-use offset remains open")
        if not frontier.delayed_ultimate_timing_closed:
            omitted.append("deliberate post-affordability Ultimate delay remains open")

        return ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("ultimate_policy", "potion_timing_policy"),
            choice_count=int(frontier.candidate_count),
            denominator_proven=bool(frontier.anchored_policy_denominator_proven),
            omitted_scope=tuple(omitted),
            _resolver=lambda index: frontier_service.candidate_at(
                build=build,
                seed=seed,
                potion_cooldown_seconds=float(potion_cooldown_seconds),
                starting_ultimate=float(starting_ultimate),
                index=index,
                ultimate_generation_events=tuple(ultimate_generation_events),
                heroism_windows=tuple(heroism_windows),
                use_scheduled_combat_attacks_for_ultimate=bool(
                    use_scheduled_combat_attacks_for_ultimate
                ),
            ),
        )

    @classmethod
    def execute_policy(
        cls,
        frontier: ExtremeSustainedDPSExecutePolicyFrontier,
    ) -> ExtremeSustainedDPSIndexedWholePlanAdapter[ExtremeSustainedDPSExecutePolicyCandidate]:
        rows = tuple(frontier.candidates)
        return ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("execute_policy",),
            choice_count=len(rows),
            denominator_proven=bool(frontier.denominator_proven),
            omitted_scope=(),
            _resolver=lambda index: rows[index],
        )

    @classmethod
    def heavy_attack_policy(
        cls,
        frontier: ExtremeSustainedDPSHeavyAttackPolicyFrontier,
    ) -> ExtremeSustainedDPSIndexedWholePlanAdapter[ExtremeSustainedDPSHeavyAttackPolicyCandidate]:
        rows = tuple(frontier.candidates)
        return ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("heavy_attack_policy",),
            choice_count=len(rows),
            denominator_proven=bool(frontier.denominator_proven),
            omitted_scope=(
                "Heavy Attack windows outside the caller-reviewed safe set remain open",
            ),
            _resolver=lambda index: rows[index],
        )


__all__ = [
    "ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService",
    "ExtremeSustainedDPSIndexedWholePlanAdapter",
]
