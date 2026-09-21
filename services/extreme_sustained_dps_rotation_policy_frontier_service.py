from __future__ import annotations

"""Generated sustained-DPS Ultimate/potion policy family over one seed RotationPlan.

This layer owns policy enumeration only. Ultimate affordability/spend remains canonical
in RotationUltimateService and final Ultimate/potion legality remains canonical in
RotationScheduledActionResourceLegalityService.

Potion timing intentionally exposes an anchored finite policy family rather than
pretending continuous-time closure: first use may occur at one existing seed-plan
action timestamp before the effective cooldown boundary, with before/after ordering
preserved when another action shares that timestamp. Repeated uses then follow the
caller-proven effective cooldown.
"""

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_generation_sources import HeroismWindow
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationPlanCandidate,
)
from services.rotation_scheduled_action_resource_legality_service import (
    RotationScheduledActionResourceAssessment,
    RotationScheduledActionResourceLegalityService,
)
from services.rotation_ultimate_service import RotationUltimateProjection, RotationUltimateService


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionTimingPolicy:
    policy_id: str
    first_use_seconds: float | None
    same_timestamp_order: str = "none"


@dataclass(frozen=True)
class ExtremeSustainedDPSRotationPolicyFrontier:
    ultimate_options: tuple[str, ...]
    potion_policies: tuple[ExtremeSustainedDPSPotionTimingPolicy, ...]
    candidate_count: int
    anchored_policy_denominator_proven: bool
    continuous_potion_timing_closed: bool
    delayed_ultimate_timing_closed: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSRotationPolicyCandidate:
    structural_index: int
    ultimate_option: str
    potion_policy: ExtremeSustainedDPSPotionTimingPolicy
    plan: RotationPlan
    ultimate_projection: RotationUltimateProjection | None
    resource_legality: RotationScheduledActionResourceAssessment
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return (
            self.resource_legality.is_legal
            and not self.plan.unresolved
            and not self.unresolved
        )


class ExtremeSustainedDPSRotationPolicyFrontierService:
    """Enumerate explicit Ultimate-choice and anchored potion-cadence policies."""

    _COMPETING_ULTIMATE_DIAGNOSTIC = "choice policy is unresolved"

    def __init__(
        self,
        *,
        ultimate_service: RotationUltimateService | object,
        legality_service: RotationScheduledActionResourceLegalityService | object | None = None,
    ) -> None:
        self.ultimate_service = ultimate_service
        self.legality_service = (
            legality_service or RotationScheduledActionResourceLegalityService()
        )

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSRotationPolicyFrontierService":
        return cls(ultimate_service=RotationUltimateService(database_path))

    @staticmethod
    def _slot_six(build: PlayerBuild, bar: str) -> str:
        values = (
            build.BackBarSkills
            if str(bar or "").strip().casefold() == "back"
            else build.FrontBarSkills
        )
        skills = list(values or [])
        if len(skills) < 6:
            return ""
        return str(skills[5] or "").strip()

    @classmethod
    def _ultimate_options(cls, build: PlayerBuild) -> tuple[str, ...]:
        values = ["none"]
        if cls._slot_six(build, "front"):
            values.append("front")
        if cls._slot_six(build, "back"):
            values.append("back")
        return tuple(values)

    @staticmethod
    def _anchor_times(
        plan: RotationPlan,
        *,
        potion_cooldown_seconds: float,
    ) -> tuple[float, ...]:
        cooldown = float(potion_cooldown_seconds)
        limit = min(float(plan.duration_seconds), cooldown)
        values = {
            float(action.time_seconds)
            for action in plan.actions
            if 0.0 <= float(action.time_seconds) < limit - 1e-9
        }
        if plan.duration_seconds >= 0.0:
            values.add(0.0)
        return tuple(sorted(values))

    @classmethod
    def _potion_policies(
        cls,
        build: PlayerBuild,
        plan: RotationPlan,
        *,
        potion_cooldown_seconds: float,
    ) -> tuple[ExtremeSustainedDPSPotionTimingPolicy, ...]:
        potion = str(build.Potion or "").strip()
        result = [
            ExtremeSustainedDPSPotionTimingPolicy(
                policy_id="potion:none",
                first_use_seconds=None,
                same_timestamp_order="none",
            )
        ]
        if not potion:
            return tuple(result)

        for time_seconds in cls._anchor_times(
            plan,
            potion_cooldown_seconds=potion_cooldown_seconds,
        ):
            for order in ("before", "after"):
                result.append(
                    ExtremeSustainedDPSPotionTimingPolicy(
                        policy_id=f"potion:{time_seconds:g}:{order}",
                        first_use_seconds=float(time_seconds),
                        same_timestamp_order=order,
                    )
                )
        return tuple(result)

    def frontier(
        self,
        *,
        build: PlayerBuild,
        seed: ExtremeSustainedDPSRotationPlanCandidate,
        potion_cooldown_seconds: float,
    ) -> ExtremeSustainedDPSRotationPolicyFrontier:
        cooldown = float(potion_cooldown_seconds)
        if not math.isfinite(cooldown) or cooldown <= 0.0:
            raise ValueError("generated potion cooldown must be finite and positive")

        ultimate_options = self._ultimate_options(build)
        potion_policies = self._potion_policies(
            build,
            seed.plan,
            potion_cooldown_seconds=cooldown,
        )
        unresolved = list(seed.unresolved)
        count = len(ultimate_options) * len(potion_policies)

        return ExtremeSustainedDPSRotationPolicyFrontier(
            ultimate_options=ultimate_options,
            potion_policies=potion_policies,
            candidate_count=count,
            anchored_policy_denominator_proven=bool(count > 0 and not unresolved),
            continuous_potion_timing_closed=False,
            delayed_ultimate_timing_closed=False,
            evidence=(
                f"Ultimate policy choices: {len(ultimate_options)}",
                f"Anchored potion timing policies: {len(potion_policies)}",
                f"Combined Ultimate/potion policy candidates: {count}",
                "Ultimate bar choice is explicit; canonical affordability scheduling remains owned by RotationUltimateService",
                "Potion first-use anchors come only from seed-plan timestamps before the effective cooldown boundary, plus explicit no-use",
                "Before/after same-timestamp potion ordering is preserved",
                "Continuous potion timing and deliberate post-affordability Ultimate delay are not claimed closed by this frontier",
            ),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )

    @staticmethod
    def _without_choice_diagnostic(plan: RotationPlan) -> RotationPlan:
        unresolved = tuple(
            item
            for item in plan.unresolved
            if ExtremeSustainedDPSRotationPolicyFrontierService._COMPETING_ULTIMATE_DIAGNOSTIC
            not in str(item).casefold()
        )
        if unresolved == plan.unresolved:
            return plan
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=plan.actions,
            assumptions=tuple(plan.assumptions)
            + ("generated sustained-DPS policy explicitly selected the competing Ultimate bar",),
            unresolved=unresolved,
        )

    @staticmethod
    def _insert_one_potion(
        plan: RotationPlan,
        *,
        potion_name: str,
        time_seconds: float,
        order: str,
    ) -> RotationPlan:
        target = float(time_seconds)
        same = [
            action
            for action in plan.actions
            if abs(float(action.time_seconds) - target) <= 1e-9
        ]
        others = [
            action
            for action in plan.actions
            if abs(float(action.time_seconds) - target) > 1e-9
        ]

        if order == "before" and same:
            shifted = [
                RotationAction(
                    time_seconds=action.time_seconds,
                    sequence=int(action.sequence) + 1,
                    kind=action.kind,
                    name=action.name,
                    bar=action.bar,
                    target_key=action.target_key,
                )
                for action in same
            ]
            potion_sequence = 0
        else:
            shifted = same
            potion_sequence = (
                max((int(action.sequence) for action in same), default=-1) + 1
            )

        actions = [
            *others,
            *shifted,
            RotationAction(
                time_seconds=target,
                sequence=potion_sequence,
                kind=RotationActionKind.POTION,
                name=potion_name,
            ),
        ]
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=plan.assumptions,
            unresolved=plan.unresolved,
        )

    @classmethod
    def _apply_potion_policy(
        cls,
        plan: RotationPlan,
        *,
        potion_name: str,
        policy: ExtremeSustainedDPSPotionTimingPolicy,
        potion_cooldown_seconds: float,
    ) -> RotationPlan:
        if policy.first_use_seconds is None:
            return plan
        if not potion_name:
            raise ValueError("potion timing policy requires a selected build potion")

        result = plan
        time_seconds = float(policy.first_use_seconds)
        cooldown = float(potion_cooldown_seconds)
        while time_seconds <= plan.duration_seconds + 1e-9:
            result = cls._insert_one_potion(
                result,
                potion_name=potion_name,
                time_seconds=time_seconds,
                order=policy.same_timestamp_order,
            )
            time_seconds = round(time_seconds + cooldown, 9)
        return result

    def candidate_at(
        self,
        *,
        build: PlayerBuild,
        seed: ExtremeSustainedDPSRotationPlanCandidate,
        potion_cooldown_seconds: float,
        starting_ultimate: float,
        index: int,
        ultimate_generation_events: tuple[UltimateGenerationEvent, ...] = (),
        heroism_windows: tuple[HeroismWindow, ...] = (),
        use_scheduled_combat_attacks_for_ultimate: bool = False,
    ) -> ExtremeSustainedDPSRotationPolicyCandidate:
        frontier = self.frontier(
            build=build,
            seed=seed,
            potion_cooldown_seconds=potion_cooldown_seconds,
        )
        if not frontier.anchored_policy_denominator_proven:
            raise ValueError(
                "rotation policy frontier is unresolved: "
                + "; ".join(frontier.unresolved)
            )

        target = int(index)
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("rotation policy candidate index out of range")

        potion_count = len(frontier.potion_policies)
        ultimate_index = target // potion_count
        potion_index = target % potion_count
        ultimate_option = frontier.ultimate_options[ultimate_index]
        potion_policy = frontier.potion_policies[potion_index]

        plan = seed.plan
        projection: RotationUltimateProjection | None = None
        generation_events = tuple(ultimate_generation_events)
        spend_rules = ()

        if ultimate_option != "none":
            projection = self.ultimate_service.apply_generation(
                build=build,
                plan=plan,
                ultimate_bar=ultimate_option,
                starting_ultimate=float(starting_ultimate),
                generation_events=generation_events,
                heroism_windows=tuple(heroism_windows),
                use_scheduled_combat_attacks=bool(
                    use_scheduled_combat_attacks_for_ultimate
                ),
            )
            plan = self._without_choice_diagnostic(projection.plan)
            generation_events = tuple(projection.generation_events)
            spend_rules = tuple(projection.spend_rules)

        plan = self._apply_potion_policy(
            plan,
            potion_name=str(build.Potion or "").strip(),
            policy=potion_policy,
            potion_cooldown_seconds=float(potion_cooldown_seconds),
        )
        assessment = self.legality_service.assess(
            plan=plan,
            starting_ultimate=float(starting_ultimate),
            ultimate_generation_events=generation_events,
            ultimate_spend_rules=spend_rules,
            potion_cooldown_seconds=float(potion_cooldown_seconds),
        )

        unresolved = tuple(
            dict.fromkeys(
                (
                    *seed.unresolved,
                    *(projection.unresolved if projection is not None else ()),
                    *assessment.unresolved,
                )
            )
        )
        unresolved = tuple(
            item
            for item in unresolved
            if self._COMPETING_ULTIMATE_DIAGNOSTIC not in str(item).casefold()
        )

        return ExtremeSustainedDPSRotationPolicyCandidate(
            structural_index=target,
            ultimate_option=ultimate_option,
            potion_policy=potion_policy,
            plan=plan,
            ultimate_projection=projection,
            resource_legality=assessment,
            evidence=(
                f"Ultimate policy: {ultimate_option}",
                f"Potion policy: {potion_policy.policy_id}",
                f"Effective potion cooldown: {float(potion_cooldown_seconds):g}s",
                f"Starting Ultimate: {float(starting_ultimate):g}",
                "Ultimate affordability and spend use canonical RotationUltimateService evidence",
                "Final Ultimate/potion legality uses RotationScheduledActionResourceLegalityService",
            ),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSPotionTimingPolicy",
    "ExtremeSustainedDPSRotationPolicyCandidate",
    "ExtremeSustainedDPSRotationPolicyFrontier",
    "ExtremeSustainedDPSRotationPolicyFrontierService",
]
