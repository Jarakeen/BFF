from __future__ import annotations

"""Concrete indexed axes for generated sustained-DPS rotation policy refinement.

A complete assembled build first selects one finite seed/cadence RotationPlan family,
then selects one delayed-Ultimate policy for that exact plan. The underlying combined
rotation-policy frontier still exposes anchored potion policies for legacy/reference
callers, but generated Objective #32 traversal deliberately selects only its explicit
potion:none slice. Canonical potion timing is owned later by the finalized descendant
potion-timing axis after execute and Heavy Attack policy selection.
"""

from dataclasses import dataclass, replace
import math

from services.extreme_sustained_dps_generated_candidate_assembly_service import (
    ExtremeSustainedDPSAssembledCandidate,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationPlanCandidate,
    ExtremeSustainedDPSRotationPlanFrontierService,
)
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSRotationPolicyCandidate,
    ExtremeSustainedDPSRotationPolicyFrontierService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedRotationAxisState:
    assembled: ExtremeSustainedDPSAssembledCandidate
    duration_seconds: float
    potion_cooldown_seconds: float
    starting_ultimate: float
    ultimate_generation_events: tuple[object, ...] = ()
    heroism_windows: tuple[object, ...] = ()
    use_scheduled_combat_attacks_for_ultimate: bool = False
    priorities: object | None = None
    encounter_demands: tuple[object, ...] = ()
    rotation_plan: ExtremeSustainedDPSRotationPlanCandidate | None = None
    rotation_policy: ExtremeSustainedDPSRotationPolicyCandidate | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("duration_seconds", self.duration_seconds),
            ("potion_cooldown_seconds", self.potion_cooldown_seconds),
            ("starting_ultimate", self.starting_ultimate),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"generated rotation state {label} must be numeric")
            if not math.isfinite(float(value)):
                raise ValueError(f"generated rotation state {label} must be finite")
        for label, value in (
            ("ultimate_generation_events", self.ultimate_generation_events),
            ("heroism_windows", self.heroism_windows),
            ("encounter_demands", self.encounter_demands),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"generated rotation state {label} must be a tuple")
        if not isinstance(self.use_scheduled_combat_attacks_for_ultimate, bool):
            raise TypeError("generated rotation state scheduled-combat Ultimate flag must be boolean")

    @property
    def complete(self) -> bool:
        return self.rotation_policy is not None


class ExtremeSustainedDPSGeneratedRotationAxisAdapterService:
    """Adapt seed-plan and delayed-Ultimate frontiers into Objective #32 tree axes."""

    def __init__(
        self,
        *,
        rotation_plans: ExtremeSustainedDPSRotationPlanFrontierService | object,
        rotation_policies: ExtremeSustainedDPSRotationPolicyFrontierService | object,
    ) -> None:
        self.rotation_plans = rotation_plans
        self.rotation_policies = rotation_policies

    @staticmethod
    def _proven_count(
        frontier: object,
        label: str,
        *,
        proof_field: str,
    ) -> int:
        raw_count = getattr(frontier, "candidate_count", 0)
        if isinstance(raw_count, bool) or not isinstance(raw_count, int):
            raise TypeError(f"{label} candidate count must be an integer")
        count = raw_count
        unresolved = getattr(frontier, "unresolved", ())
        if not isinstance(unresolved, tuple):
            raise TypeError(f"{label} unresolved evidence must be a tuple")
        proof = getattr(frontier, proof_field, False)
        if not isinstance(proof, bool):
            raise TypeError(f"{label} denominator proof flag must be boolean")
        if not proof:
            detail = "; ".join(str(item) for item in unresolved if str(item))
            raise ValueError(
                f"{label} denominator is unresolved"
                + (f": {detail}" if detail else "")
            )
        if count <= 0:
            raise ValueError(f"{label} denominator is empty")
        return count

    def _plan_count(
        self,
        state: ExtremeSustainedDPSGeneratedRotationAxisState,
    ) -> int:
        return self._proven_count(
            self.rotation_plans.frontier(state.assembled),
            "rotation-plan frontier",
            proof_field="denominator_proven",
        )

    def _plan_at(
        self,
        state: ExtremeSustainedDPSGeneratedRotationAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedRotationAxisState:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("generated rotation-plan index must be an integer")
        candidate = self.rotation_plans.candidate_at(
            state.assembled,
            duration_seconds=state.duration_seconds,
            index=index,
            priorities=state.priorities,
            encounter_demands=state.encounter_demands,
        )
        return replace(state, rotation_plan=candidate, rotation_policy=None)

    @staticmethod
    def _require_plan(
        state: ExtremeSustainedDPSGeneratedRotationAxisState,
    ) -> ExtremeSustainedDPSRotationPlanCandidate:
        if state.rotation_plan is None:
            raise ValueError(
                "generated rotation policy requires a selected rotation-plan family"
            )
        return state.rotation_plan

    def _policy_count(
        self,
        state: ExtremeSustainedDPSGeneratedRotationAxisState,
    ) -> int:
        seed = self._require_plan(state)
        frontier = self.rotation_policies.frontier(
            build=state.assembled.build,
            seed=seed,
            potion_cooldown_seconds=state.potion_cooldown_seconds,
            starting_ultimate=state.starting_ultimate,
            ultimate_generation_events=state.ultimate_generation_events,
            heroism_windows=state.heroism_windows,
            use_scheduled_combat_attacks_for_ultimate=(
                state.use_scheduled_combat_attacks_for_ultimate
            ),
        )
        self._proven_count(
            frontier,
            "rotation policy frontier",
            proof_field="anchored_policy_denominator_proven",
        )
        policies = getattr(frontier, "ultimate_timing_policies", ())
        if not isinstance(policies, tuple):
            raise TypeError("rotation policy Ultimate timing policies must be a tuple")
        count = len(policies)
        if count <= 0:
            raise ValueError("generated delayed-Ultimate policy denominator is empty")
        return count

    def _policy_at(
        self,
        state: ExtremeSustainedDPSGeneratedRotationAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedRotationAxisState:
        seed = self._require_plan(state)
        frontier = self.rotation_policies.frontier(
            build=state.assembled.build,
            seed=seed,
            potion_cooldown_seconds=state.potion_cooldown_seconds,
            starting_ultimate=state.starting_ultimate,
            ultimate_generation_events=state.ultimate_generation_events,
            heroism_windows=state.heroism_windows,
            use_scheduled_combat_attacks_for_ultimate=(
                state.use_scheduled_combat_attacks_for_ultimate
            ),
        )
        ultimate_policies = getattr(frontier, "ultimate_timing_policies", ())
        if not isinstance(ultimate_policies, tuple):
            raise TypeError("rotation policy Ultimate timing policies must be a tuple")
        potion_policies = getattr(frontier, "potion_policies", ())
        if not isinstance(potion_policies, tuple):
            raise TypeError("rotation policy potion policies must be a tuple")
        ultimate_count = len(ultimate_policies)
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("generated delayed-Ultimate policy index must be an integer")
        target = index
        if target < 0 or target >= ultimate_count:
            raise IndexError("generated delayed-Ultimate policy index out of range")
        potion_count = len(potion_policies)
        if potion_count <= 0:
            raise ValueError("rotation policy frontier has no explicit potion:none slice")
        candidate = self.rotation_policies.candidate_at(
            build=state.assembled.build,
            seed=seed,
            potion_cooldown_seconds=state.potion_cooldown_seconds,
            starting_ultimate=state.starting_ultimate,
            index=target * potion_count,
            ultimate_generation_events=state.ultimate_generation_events,
            heroism_windows=state.heroism_windows,
            use_scheduled_combat_attacks_for_ultimate=(
                state.use_scheduled_combat_attacks_for_ultimate
            ),
        )
        return replace(state, rotation_policy=candidate)

    def root(
        self,
        assembled: ExtremeSustainedDPSAssembledCandidate,
        *,
        duration_seconds: float,
        potion_cooldown_seconds: float,
        starting_ultimate: float,
        ultimate_generation_events: tuple[object, ...] = (),
        heroism_windows: tuple[object, ...] = (),
        use_scheduled_combat_attacks_for_ultimate: bool = False,
        priorities: object | None = None,
        encounter_demands: tuple[object, ...] = (),
    ) -> ExtremeSustainedDPSGeneratedRotationAxisState:
        if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float)):
            raise TypeError("generated rotation duration must be numeric, not boolean")
        if isinstance(potion_cooldown_seconds, bool) or not isinstance(potion_cooldown_seconds, (int, float)):
            raise TypeError("generated potion cooldown must be numeric, not boolean")
        if isinstance(starting_ultimate, bool) or not isinstance(starting_ultimate, (int, float)):
            raise TypeError("generated starting Ultimate must be numeric, not boolean")
        if not isinstance(use_scheduled_combat_attacks_for_ultimate, bool):
            raise TypeError("scheduled-combat Ultimate flag must be boolean")
        for label, value in (
            ("ultimate_generation_events", ultimate_generation_events),
            ("heroism_windows", heroism_windows),
            ("encounter_demands", encounter_demands),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"generated rotation {label} must be a tuple")
        duration = float(duration_seconds)
        cooldown = float(potion_cooldown_seconds)
        ultimate = float(starting_ultimate)
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError("generated rotation duration must be finite and positive")
        if not math.isfinite(cooldown) or cooldown <= 0.0:
            raise ValueError("generated potion cooldown must be finite and positive")
        if not math.isfinite(ultimate) or ultimate < 0.0:
            raise ValueError("generated starting Ultimate must be finite and non-negative")
        return ExtremeSustainedDPSGeneratedRotationAxisState(
            assembled=assembled,
            duration_seconds=duration,
            potion_cooldown_seconds=cooldown,
            starting_ultimate=ultimate,
            ultimate_generation_events=ultimate_generation_events,
            heroism_windows=heroism_windows,
            use_scheduled_combat_attacks_for_ultimate=use_scheduled_combat_attacks_for_ultimate,
            priorities=priorities,
            encounter_demands=encounter_demands,
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Rotation Plan Family",
                candidate_count=self._plan_count,
                candidate_at=self._plan_at,
                canonical_axes=("rotation_order", "light_attack_weave"),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Delayed Ultimate Policy",
                candidate_count=self._policy_count,
                candidate_at=self._policy_at,
                canonical_axes=("ultimate_policy",),
            ),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedRotationAxisAdapterService",
    "ExtremeSustainedDPSGeneratedRotationAxisState",
]
