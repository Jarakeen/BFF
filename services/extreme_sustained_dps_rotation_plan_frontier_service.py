from __future__ import annotations

"""Lazy seed/cadence RotationPlan family frontier for assembled sustained-DPS builds.

The frontier preserves every ordinary-skill ordering on each populated bar, each legal
starting-bar route, and both Light-Attack weave states. It does not claim closure over
Ultimate timing, potion actions, execute policy, Heavy Attacks, encounter obligations,
or later duration/cadence refinements.

Canonical SemiStaticRotationPlanner builds the seed schedule. An optional canonical
RotationDurationRefinementService may then refine reviewed positive-duration recasts.
"""

from dataclasses import dataclass
from math import factorial
from pathlib import Path

from minmax.rotation_definition import RotationDefinition, RotationMode, RotationStep
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.semi_static_rotation_planner import SemiStaticRotationPlanner
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_candidate_assembly_service import (
    ExtremeSustainedDPSAssembledCandidate,
)
from services.rotation_duration_refinement_service import RotationDurationRefinementService


@dataclass(frozen=True)
class ExtremeSustainedDPSRotationFamilyFrontier:
    front_skill_count: int
    back_skill_count: int
    front_order_count: int
    back_order_count: int
    starting_route_count: int
    weave_state_count: int
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSRotationPlanCandidate:
    structural_index: int
    front_order: tuple[str, ...]
    back_order: tuple[str, ...]
    starting_bar: str
    weave_light_attacks: bool
    plan: RotationPlan
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved and not self.plan.unresolved


class ExtremeSustainedDPSRotationPlanFrontierService:
    """Index proof-neutral semi-static plan families for one assembled DD build."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        planner: SemiStaticRotationPlanner | None = None,
        refinement_service: RotationDurationRefinementService | object | None = None,
    ) -> None:
        self.database_path = Path(database_path) if database_path is not None else None
        self.planner = planner or SemiStaticRotationPlanner()
        if refinement_service is not None:
            self.refinement_service = refinement_service
        elif self.database_path is not None:
            self.refinement_service = RotationDurationRefinementService(self.database_path)
        else:
            self.refinement_service = None

    @staticmethod
    def _ordinary_skills(build: PlayerBuild, bar: str) -> tuple[str, ...]:
        values = (
            build.BackBarSkills
            if str(bar or "").strip().casefold() == "back"
            else build.FrontBarSkills
        )
        return tuple(
            str(value or "").strip()
            for value in list(values or [])[:5]
            if str(value or "").strip()
        )

    @staticmethod
    def _permutation_at(values: tuple[str, ...], index: int) -> tuple[str, ...]:
        n = len(values)
        total = factorial(n)
        target = int(index)
        if target < 0 or target >= total:
            raise IndexError("rotation skill-order permutation index out of range")
        pool = list(values)
        result: list[str] = []
        for remaining in range(n, 0, -1):
            block = factorial(remaining - 1)
            local = target // block
            target %= block
            result.append(pool.pop(local))
        return tuple(result)

    def frontier(
        self,
        candidate: ExtremeSustainedDPSAssembledCandidate,
    ) -> ExtremeSustainedDPSRotationFamilyFrontier:
        front = self._ordinary_skills(candidate.build, "front")
        back = self._ordinary_skills(candidate.build, "back")
        unresolved = list(candidate.unresolved)

        if not front and not back:
            unresolved.append(
                "Generated rotation family requires at least one ordinary slotted skill"
            )

        front_orders = factorial(len(front))
        back_orders = factorial(len(back))
        route_count = 2 if front and back else 1
        weave_count = 2
        count = front_orders * back_orders * route_count * weave_count
        if not front and not back:
            count = 0

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeSustainedDPSRotationFamilyFrontier(
            front_skill_count=len(front),
            back_skill_count=len(back),
            front_order_count=front_orders,
            back_order_count=back_orders,
            starting_route_count=route_count,
            weave_state_count=weave_count,
            candidate_count=count,
            denominator_proven=bool(count > 0 and not final_unresolved),
            evidence=(
                f"Front ordinary skills: {len(front)} ({front_orders} orderings)",
                f"Back ordinary skills: {len(back)} ({back_orders} orderings)",
                f"Legal starting-bar routes: {route_count}",
                f"Light-Attack weave states: {weave_count}",
                f"Seed/cadence rotation family denominator: {count}",
                "Finite-horizon start-bar order remains explicit because early/late damage timing can differ",
                "Ultimate, potion, execute, Heavy Attack, encounter-demand, and broader policy families remain separate open rotation axes",
            ),
            unresolved=final_unresolved,
        )

    @staticmethod
    def _normalized_build(
        candidate: ExtremeSustainedDPSAssembledCandidate,
    ) -> PlayerBuild:
        build = PlayerBuild.from_dict(candidate.build.to_dict())
        if not str(build.Name or "").strip():
            build.Name = "Generated Sustained DPS Candidate"
        if not str(build.BuildName or "").strip():
            build.BuildName = f"Generated {candidate.coordinate.identity}"
        return build

    @staticmethod
    def _steps(
        *,
        front_order: tuple[str, ...],
        back_order: tuple[str, ...],
        starting_bar: str,
    ) -> tuple[RotationStep, ...]:
        start = str(starting_bar or "").strip().casefold()
        if start not in {"front", "back"}:
            raise ValueError("generated rotation starting bar must be front or back")

        first = front_order if start == "front" else back_order
        second = back_order if start == "front" else front_order
        other = "back" if start == "front" else "front"

        steps: list[RotationStep] = [
            RotationStep(
                kind=RotationActionKind.SKILL,
                name=name,
                bar=start,
            )
            for name in first
        ]
        if second:
            steps.append(RotationStep(kind=RotationActionKind.BAR_SWAP, bar=other))
            steps.extend(
                RotationStep(
                    kind=RotationActionKind.SKILL,
                    name=name,
                    bar=other,
                )
                for name in second
            )
            if first:
                steps.append(RotationStep(kind=RotationActionKind.BAR_SWAP, bar=start))
        if not steps:
            raise ValueError("generated rotation family has no ordinary skill steps")
        return tuple(steps)

    def candidate_at(
        self,
        candidate: ExtremeSustainedDPSAssembledCandidate,
        *,
        duration_seconds: float,
        index: int,
        priorities: AbilityPriorityList | None = None,
        encounter_demands: tuple[RotationDemandWindow, ...] = (),
    ) -> ExtremeSustainedDPSRotationPlanCandidate:
        frontier = self.frontier(candidate)
        if not frontier.denominator_proven:
            raise ValueError(
                "generated rotation family denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )

        target = int(index)
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("generated rotation-plan candidate index out of range")
        duration = float(duration_seconds)
        if duration <= 0.0:
            raise ValueError("generated rotation duration must be positive")

        build = self._normalized_build(candidate)
        front = self._ordinary_skills(build, "front")
        back = self._ordinary_skills(build, "back")

        weave = bool(target % frontier.weave_state_count)
        target //= frontier.weave_state_count

        if frontier.starting_route_count == 2:
            route_index = target % 2
            target //= 2
            starting_bar = "front" if route_index == 0 else "back"
        else:
            starting_bar = "front" if front else "back"

        back_index = target % frontier.back_order_count
        target //= frontier.back_order_count
        front_index = target % frontier.front_order_count

        front_order = self._permutation_at(front, front_index)
        back_order = self._permutation_at(back, back_index)

        definition = RotationDefinition(
            character_name=str(build.Name).strip(),
            build_name=str(build.BuildName).strip(),
            duration_seconds=duration,
            steps=self._steps(
                front_order=front_order,
                back_order=back_order,
                starting_bar=starting_bar,
            ),
            mode=RotationMode.SEMI_STATIC,
            action_interval_seconds=1.0,
            initial_bar=starting_bar,
            weave_light_attacks=weave,
            assumptions=(
                "generated sustained-DPS seed family uses canonical 1.0s action interval",
                "ordinary skill order, starting bar, and Light-Attack weave are explicit generated coordinates",
            ),
            unresolved=(),
        )
        plan = self.planner.build_plan(definition, build)

        if self.refinement_service is not None:
            refined = self.refinement_service.refine(
                plan,
                priorities=priorities,
                demands=tuple(encounter_demands),
            )
            plan = refined.plan

        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in plan.unresolved
                if str(item).strip()
            )
        )
        return ExtremeSustainedDPSRotationPlanCandidate(
            structural_index=int(index),
            front_order=front_order,
            back_order=back_order,
            starting_bar=starting_bar,
            weave_light_attacks=weave,
            plan=plan,
            evidence=(
                f"Rotation family index: {int(index)}",
                f"Starting bar: {starting_bar}",
                f"Light-Attack weave: {weave}",
                f"Plan horizon: {duration:g}s",
                "Seed schedule built by canonical SemiStaticRotationPlanner",
                (
                    "Canonical duration refinement applied"
                    if self.refinement_service is not None
                    else "Duration refinement not supplied to this frontier instance"
                ),
                f"Encounter demand windows supplied: {len(tuple(encounter_demands))}",
            ),
            unresolved=unresolved,
        )

    def page(
        self,
        candidate: ExtremeSustainedDPSAssembledCandidate,
        *,
        duration_seconds: float,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSRotationPlanCandidate, ...]:
        frontier = self.frontier(candidate)
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(
                candidate,
                duration_seconds=duration_seconds,
                index=index,
            )
            for index in range(start, min(frontier.candidate_count, start + size))
        )


__all__ = [
    "ExtremeSustainedDPSRotationFamilyFrontier",
    "ExtremeSustainedDPSRotationPlanCandidate",
    "ExtremeSustainedDPSRotationPlanFrontierService",
]
