from __future__ import annotations

"""Late finalized potion-timing axis for generated sustained-DPS search.

The axis begins only after execute/Heavy-Attack policy selection has produced the
finalized GeneratedRotationCandidate. A caller-owned timing-evidence resolver supplies
reviewed periodic projections and verified Heavy Attack completion evidence for that
exact candidate. Canonical potion duration math and continuous-time reduction remain
owned by the existing finalized-denominator services.
"""

from dataclasses import dataclass, replace
from typing import Protocol

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_finalized_potion_timing_denominator_service import (
    ExtremeSustainedDPSFinalizedPotionTimingDenominator,
    ExtremeSustainedDPSFinalizedPotionTimingDenominatorService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_potion_observation_frontier_service import (
    ExtremeSustainedDPSPotionObservationFrontierService,
)
from services.extreme_sustained_dps_potion_timing_breakpoint_frontier_service import (
    ExtremeSustainedDPSPotionTimingBreakpointChoice,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_scheduled_action_resource_legality_service import (
    RotationScheduledActionResourceLegalityService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSFinalizedPotionTimingEvidence:
    periodic_projections: tuple[object, ...] = ()
    heavy_attack_completion_evidence: tuple[object, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeSustainedDPSFinalizedPotionTimingEvidenceResolver(Protocol):
    def __call__(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> ExtremeSustainedDPSFinalizedPotionTimingEvidence: ...


@dataclass(frozen=True)
class ExtremeSustainedDPSFinalizedPotionTimingPolicy:
    policy_id: str
    first_use_seconds: float | None
    same_timestamp_order: str
    source_choice: ExtremeSustainedDPSPotionTimingBreakpointChoice | None = None


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedFinalizedPotionAxisState:
    upstream_state: object
    build: object
    progression: object
    potion_cooldown_seconds: float
    candidate: GeneratedRotationCandidate
    evidence_resolver: ExtremeSustainedDPSFinalizedPotionTimingEvidenceResolver
    selected_policy: ExtremeSustainedDPSFinalizedPotionTimingPolicy | None = None
    denominator: ExtremeSustainedDPSFinalizedPotionTimingDenominator | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.selected_policy is not None and not self.unresolved

    def __getattr__(self, name: str):
        return getattr(self.upstream_state, name)


class ExtremeSustainedDPSGeneratedFinalizedPotionAxisAdapterService:
    """Enumerate exact finalized potion timing after all timing-producing policies."""

    _EPSILON = 1e-9

    def __init__(
        self,
        *,
        denominator_service: ExtremeSustainedDPSFinalizedPotionTimingDenominatorService | None = None,
        legality_service: RotationScheduledActionResourceLegalityService | None = None,
    ) -> None:
        self.denominator_service = (
            denominator_service
            or ExtremeSustainedDPSFinalizedPotionTimingDenominatorService()
        )
        self.legality_service = legality_service or RotationScheduledActionResourceLegalityService()

    @staticmethod
    def _strip_potions(plan: RotationPlan) -> RotationPlan:
        actions = tuple(
            action
            for action in plan.actions
            if action.kind is not RotationActionKind.POTION
        )
        if actions == plan.actions:
            return plan
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=actions,
            assumptions=plan.assumptions,
            unresolved=plan.unresolved,
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
            potion_sequence = max(
                (int(action.sequence) for action in same),
                default=-1,
            ) + 1

        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(
                [
                    *others,
                    *shifted,
                    RotationAction(
                        time_seconds=target,
                        sequence=potion_sequence,
                        kind=RotationActionKind.POTION,
                        name=potion_name,
                    ),
                ]
            ),
            assumptions=plan.assumptions,
            unresolved=plan.unresolved,
        )

    @classmethod
    def _apply_policy(
        cls,
        plan: RotationPlan,
        *,
        potion_name: str,
        policy: ExtremeSustainedDPSFinalizedPotionTimingPolicy,
        cooldown_seconds: float,
    ) -> RotationPlan:
        base = cls._strip_potions(plan)
        if policy.first_use_seconds is None:
            return base
        if not potion_name:
            raise ValueError("finalized potion timing policy requires selected potion")

        result = base
        time_seconds = float(policy.first_use_seconds)
        while time_seconds <= float(plan.duration_seconds) + cls._EPSILON:
            result = cls._insert_one_potion(
                result,
                potion_name=potion_name,
                time_seconds=time_seconds,
                order=policy.same_timestamp_order,
            )
            time_seconds = round(time_seconds + float(cooldown_seconds), 9)
        return result

    @staticmethod
    def _current_candidate(upstream_state: object) -> GeneratedRotationCandidate:
        runtime = getattr(upstream_state, "runtime", None)
        candidate = getattr(runtime, "current_candidate", None)
        if candidate is None:
            candidate = getattr(upstream_state, "current_candidate", None)
        if candidate is None:
            raise ValueError(
                "finalized potion timing axis requires complete runtime policy candidate"
            )
        return candidate

    def root(
        self,
        upstream_state: object,
        *,
        build: object,
        progression: object,
        potion_cooldown_seconds: float,
        evidence_resolver: ExtremeSustainedDPSFinalizedPotionTimingEvidenceResolver,
    ) -> ExtremeSustainedDPSGeneratedFinalizedPotionAxisState:
        runtime_stage = getattr(upstream_state, "runtime", None)
        runtime_complete = bool(
            runtime_stage is not None
            and getattr(runtime_stage, "complete", False)
        )
        if not runtime_complete and not bool(getattr(upstream_state, "complete", False)):
            raise ValueError(
                "finalized potion timing axis requires complete upstream runtime policy state"
            )
        if evidence_resolver is None:
            raise ValueError(
                "finalized potion timing axis requires explicit timing-evidence resolver"
            )
        candidate = self._current_candidate(upstream_state)
        return ExtremeSustainedDPSGeneratedFinalizedPotionAxisState(
            upstream_state=upstream_state,
            build=build,
            progression=progression,
            potion_cooldown_seconds=float(potion_cooldown_seconds),
            candidate=candidate,
            evidence_resolver=evidence_resolver,
        )

    def _denominator(
        self,
        state: ExtremeSustainedDPSGeneratedFinalizedPotionAxisState,
    ) -> ExtremeSustainedDPSFinalizedPotionTimingDenominator | None:
        potion_name = " ".join(
            str(getattr(state.build, "Potion", "") or "").strip().split()
        )
        if not potion_name:
            return None

        evidence = state.evidence_resolver(state.candidate)
        evidence_unresolved = tuple(
            str(item).strip()
            for item in tuple(getattr(evidence, "unresolved", ()) or ())
            if str(item).strip()
        )
        if evidence_unresolved:
            raise ValueError(
                "finalized potion timing evidence is unresolved: "
                + "; ".join(evidence_unresolved)
            )

        observations = ExtremeSustainedDPSPotionObservationFrontierService.collect(
            plan=self._strip_potions(state.candidate.plan),
            periodic_projections=tuple(
                getattr(evidence, "periodic_projections", ()) or ()
            ),
            heavy_attack_completion_evidence=tuple(
                getattr(evidence, "heavy_attack_completion_evidence", ()) or ()
            ),
        )
        denominator = self.denominator_service.build(
            player_build=state.build,
            progression=state.progression,
            observation_frontier=observations,
            duration_seconds=float(state.candidate.plan.duration_seconds),
            cooldown_seconds=float(state.potion_cooldown_seconds),
            instant_restoration_timing_closed=True,
        )
        if not denominator.denominator_proven:
            detail = "; ".join(denominator.unresolved)
            raise ValueError(
                "finalized potion timing denominator is unresolved"
                + (f": {detail}" if detail else "")
            )
        if not denominator.breakpoint_frontier.full_potion_timing_closed:
            raise ValueError(
                "finalized potion timing denominator did not close full timing scope"
            )
        return denominator

    def _policies(
        self,
        state: ExtremeSustainedDPSGeneratedFinalizedPotionAxisState,
    ) -> tuple[ExtremeSustainedDPSFinalizedPotionTimingPolicy, ...]:
        potion_name = " ".join(
            str(getattr(state.build, "Potion", "") or "").strip().split()
        )
        no_use = ExtremeSustainedDPSFinalizedPotionTimingPolicy(
            policy_id="potion:none",
            first_use_seconds=None,
            same_timestamp_order="none",
        )
        if not potion_name:
            return (no_use,)

        denominator = self._denominator(state)
        assert denominator is not None
        policies: list[ExtremeSustainedDPSFinalizedPotionTimingPolicy] = [no_use]

        observation_times = set(denominator.observation_frontier.observation_times)
        for choice in denominator.breakpoint_frontier.choices:
            time_seconds = float(choice.first_use_seconds)
            if time_seconds in observation_times:
                orders = ("before", "after")
            else:
                orders = ("after",)
            for order in orders:
                policies.append(
                    ExtremeSustainedDPSFinalizedPotionTimingPolicy(
                        policy_id=(
                            f"potion:{time_seconds:g}:{order}:"
                            f"{choice.kind}"
                        ),
                        first_use_seconds=time_seconds,
                        same_timestamp_order=order,
                        source_choice=choice,
                    )
                )
        return tuple(policies)

    def _count(
        self,
        state: ExtremeSustainedDPSGeneratedFinalizedPotionAxisState,
    ) -> int:
        policies = self._policies(state)
        if not policies:
            raise ValueError("finalized potion timing denominator is empty")
        return len(policies)

    def _at(
        self,
        state: ExtremeSustainedDPSGeneratedFinalizedPotionAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedFinalizedPotionAxisState:
        policies = self._policies(state)
        target = int(index)
        if target < 0 or target >= len(policies):
            raise IndexError("finalized potion timing policy index out of range")
        policy = policies[target]

        potion_name = " ".join(
            str(getattr(state.build, "Potion", "") or "").strip().split()
        )
        plan = self._apply_policy(
            state.candidate.plan,
            potion_name=potion_name,
            policy=policy,
            cooldown_seconds=state.potion_cooldown_seconds,
        )

        # This late axis changes potion timing only. Ultimate spend/generation was
        # already proven upstream; the legality pass here is therefore limited to
        # deterministic potion cooldown/order validation.
        assessment = self.legality_service.assess(
            plan=plan,
            starting_ultimate=0.0,
            ultimate_generation_events=(),
            ultimate_spend_rules=(),
            potion_cooldown_seconds=state.potion_cooldown_seconds,
        )
        potion_unresolved = tuple(
            item
            for item in assessment.unresolved
            if "potion" in str(item).casefold()
        )

        candidate = replace(
            state.candidate,
            candidate_id=f"{state.candidate.candidate_id}|final-potion:{target}",
            plan=plan,
        )
        denominator = self._denominator(state)
        return replace(
            state,
            candidate=candidate,
            selected_policy=policy,
            denominator=denominator,
            unresolved=tuple(dict.fromkeys(potion_unresolved)),
        )

    def axis(self) -> ExtremeSustainedDPSIndexedFrontierAxis:
        return ExtremeSustainedDPSIndexedFrontierAxis(
            "Finalized Potion Timing Policy",
            candidate_count=self._count,
            candidate_at=self._at,
            canonical_axes=("potion_timing_policy",),
        )


__all__ = [
    "ExtremeSustainedDPSFinalizedPotionTimingEvidence",
    "ExtremeSustainedDPSFinalizedPotionTimingEvidenceResolver",
    "ExtremeSustainedDPSFinalizedPotionTimingPolicy",
    "ExtremeSustainedDPSGeneratedFinalizedPotionAxisAdapterService",
    "ExtremeSustainedDPSGeneratedFinalizedPotionAxisState",
]
