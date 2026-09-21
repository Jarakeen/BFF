from __future__ import annotations

"""Prove maximum damage-action counts for generated semi-static rotation families.

Canonical SemiStaticRotationPlanner advances one authored step every fixed action
interval and repeats the step cycle through the inclusive plan horizon. Generated seed
families differ by ordinary-skill ordering, legal starting bar, and Light-Attack weave
state, but ordinary ordering does not change which cycle positions are skill steps.

This service reconstructs only the generated frontier's step-kind pattern and counts
the maximum damage-bearing actions over all legal start-bar routes and weave states.
Open policy descendants may add extra damage actions (notably Ultimate casts), so a
caller must separately prove their maximum additional count before this becomes a
ceiling for the broader descendant branch.
"""

from dataclasses import dataclass
from math import floor, isfinite

from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationFamilyFrontier,
)
from services.extreme_sustained_dps_structural_action_upper_bound_service import (
    ExtremeSustainedDPSDamageActionCountProof,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSAdditionalDamageActionCountProof:
    maximum_additional_damage_actions: int | None
    proven_safe: bool
    source: str
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.maximum_additional_damage_actions is not None:
            count = int(self.maximum_additional_damage_actions)
            if count < 0:
                raise ValueError("maximum additional damage-action count cannot be negative")
            object.__setattr__(self, "maximum_additional_damage_actions", count)
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )

    @property
    def complete(self) -> bool:
        return (
            self.maximum_additional_damage_actions is not None
            and self.proven_safe
            and not self.unresolved
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSRotationFamilyActionCountResult:
    seed_maximum_damage_action_count: int
    maximum_damage_action_count: int | None
    proof: ExtremeSustainedDPSDamageActionCountProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSRotationFamilyActionCountProofService:
    """Count seed-family damage actions without enumerating skill permutations."""

    @staticmethod
    def _step_pattern(
        *,
        front_skill_count: int,
        back_skill_count: int,
        starting_bar: str,
    ) -> tuple[bool, ...]:
        front = int(front_skill_count)
        back = int(back_skill_count)
        start = str(starting_bar or "").strip().casefold()

        first = front if start == "front" else back
        second = back if start == "front" else front

        pattern: list[bool] = [True] * first
        if second:
            pattern.append(False)  # bar swap
            pattern.extend([True] * second)
            if first:
                pattern.append(False)  # return swap
        if not pattern:
            raise ValueError("rotation family step pattern cannot be empty")
        return tuple(pattern)

    @classmethod
    def _seed_action_count(
        cls,
        *,
        front_skill_count: int,
        back_skill_count: int,
        duration_seconds: float,
        action_interval_seconds: float,
        starting_bar: str,
        weave_light_attacks: bool,
    ) -> int:
        duration = float(duration_seconds)
        interval = float(action_interval_seconds)
        tick_count = int(floor(duration / interval + 1e-12)) + 1
        pattern = cls._step_pattern(
            front_skill_count=front_skill_count,
            back_skill_count=back_skill_count,
            starting_bar=starting_bar,
        )
        damage_actions = 0
        multiplier = 2 if weave_light_attacks else 1
        for tick in range(tick_count):
            if pattern[tick % len(pattern)]:
                damage_actions += multiplier
        return int(damage_actions)

    @classmethod
    def prove(
        cls,
        frontier: ExtremeSustainedDPSRotationFamilyFrontier,
        *,
        duration_seconds: float,
        action_interval_seconds: float = 1.0,
        additional_policy_damage_actions: ExtremeSustainedDPSAdditionalDamageActionCountProof | None = None,
    ) -> ExtremeSustainedDPSRotationFamilyActionCountResult:
        duration = float(duration_seconds)
        interval = float(action_interval_seconds)
        if not isfinite(duration) or duration <= 0.0:
            raise ValueError("rotation-family action-count duration must be finite and positive")
        if not isfinite(interval) or interval <= 0.0:
            raise ValueError("rotation-family action interval must be finite and positive")

        unresolved = list(frontier.unresolved)
        routes: tuple[str, ...]
        if frontier.front_skill_count and frontier.back_skill_count:
            routes = ("front", "back")
        elif frontier.front_skill_count:
            routes = ("front",)
        elif frontier.back_skill_count:
            routes = ("back",)
        else:
            routes = ()

        if not routes:
            unresolved.append("Rotation family has no populated ordinary-skill bar")

        seed_counts = tuple(
            cls._seed_action_count(
                front_skill_count=frontier.front_skill_count,
                back_skill_count=frontier.back_skill_count,
                duration_seconds=duration,
                action_interval_seconds=interval,
                starting_bar=route,
                weave_light_attacks=weave,
            )
            for route in routes
            for weave in (False, True)
        )
        seed_max = max(seed_counts, default=0)

        maximum = None
        proven_safe = bool(
            frontier.denominator_proven
            and routes
            and not unresolved
        )

        if additional_policy_damage_actions is None:
            maximum = seed_max
        elif additional_policy_damage_actions.complete:
            maximum = (
                seed_max
                + int(additional_policy_damage_actions.maximum_additional_damage_actions)
            )
        else:
            unresolved.extend(additional_policy_damage_actions.unresolved)
            if additional_policy_damage_actions.maximum_additional_damage_actions is None:
                unresolved.append(
                    "Maximum additional policy damage-action count is unavailable"
                )
            elif not additional_policy_damage_actions.proven_safe:
                unresolved.append(
                    "Maximum additional policy damage-action count is not proven safe"
                )
            proven_safe = False

        proof = ExtremeSustainedDPSDamageActionCountProof(
            maximum_damage_action_count=maximum,
            proven_safe=bool(proven_safe and maximum is not None),
            source=(
                "canonical generated semi-static step-pattern count"
                + (
                    " plus proven additional policy damage-action ceiling"
                    if additional_policy_damage_actions is not None
                    else ""
                )
            ),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
        return ExtremeSustainedDPSRotationFamilyActionCountResult(
            seed_maximum_damage_action_count=seed_max,
            maximum_damage_action_count=maximum,
            proof=proof,
            evidence=(
                f"Front ordinary-skill count: {frontier.front_skill_count}",
                f"Back ordinary-skill count: {frontier.back_skill_count}",
                f"Comparison horizon: {duration:g}s",
                f"Canonical authored-step interval: {interval:g}s",
                f"Maximum seed-family damage-bearing actions: {seed_max}",
                (
                    f"Maximum descendant damage-bearing actions: {maximum}"
                    if maximum is not None
                    else "Maximum descendant damage-bearing actions: unresolved"
                ),
                "Ordinary-skill permutation does not change the generated step-kind cycle",
                "Light-Attack weave-on is included when taking the seed-family maximum",
            ),
            unresolved=proof.unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSAdditionalDamageActionCountProof",
    "ExtremeSustainedDPSRotationFamilyActionCountProofService",
    "ExtremeSustainedDPSRotationFamilyActionCountResult",
]
