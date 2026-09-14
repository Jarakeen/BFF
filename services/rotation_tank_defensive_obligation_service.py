from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleHardObligationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


_DEFENSIVE_KINDS = frozenset(
    {
        RotationActionKind.BLOCK,
        RotationActionKind.DODGE,
    }
)


@dataclass(frozen=True)
class RotationTankDefensiveObligation:
    """Explicit source-backed defensive response requirement for one time window.

    This contract owns only the required response action and its timing window. It
    does not infer whether a mechanic is blockable/dodgeable, does not calculate
    mitigation, and does not invent encounter timing from prose. Those facts must be
    supplied by reviewed encounter/policy evidence before this obligation is built.
    """

    obligation_id: str
    window_start_seconds: float
    window_end_seconds: float
    allowed_actions: tuple[RotationActionKind, ...]
    minimum_responses: int = 1
    bar: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        obligation_id = str(self.obligation_id or "").strip()
        if not obligation_id:
            raise ValueError("tank defensive obligation_id is required")
        object.__setattr__(self, "obligation_id", obligation_id)

        start = float(self.window_start_seconds)
        end = float(self.window_end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("tank defensive window start must be finite and non-negative")
        if not math.isfinite(end) or end < start:
            raise ValueError("tank defensive window end must be finite and >= start")
        object.__setattr__(self, "window_start_seconds", start)
        object.__setattr__(self, "window_end_seconds", end)

        actions: list[RotationActionKind] = []
        for raw_action in self.allowed_actions:
            action = (
                raw_action
                if isinstance(raw_action, RotationActionKind)
                else RotationActionKind(str(raw_action))
            )
            if action not in _DEFENSIVE_KINDS:
                raise ValueError(
                    "tank defensive obligation actions must be block and/or dodge"
                )
            if action not in actions:
                actions.append(action)
        if not actions:
            raise ValueError("tank defensive obligation requires an allowed action")
        object.__setattr__(self, "allowed_actions", tuple(actions))

        minimum = int(self.minimum_responses)
        if minimum < 1:
            raise ValueError("tank defensive minimum_responses must be positive")
        object.__setattr__(self, "minimum_responses", minimum)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank defensive obligation bar must be front or back")
            object.__setattr__(self, "bar", bar)

        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.provenance
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class RotationTankDefensiveObligationAssessment:
    obligation_id: str
    satisfied: bool
    matching_actions: tuple[RotationAction, ...]
    required_responses: int
    provenance: tuple[str, ...] = ()


class RotationTankDefensiveObligationService:
    """Assess exact scheduled block/dodge responses against explicit obligations."""

    @staticmethod
    def assess(
        *,
        plan: RotationPlan,
        obligation: RotationTankDefensiveObligation,
    ) -> RotationTankDefensiveObligationAssessment:
        matching = tuple(
            action
            for action in plan.actions
            if obligation.window_start_seconds
            <= float(action.time_seconds)
            <= obligation.window_end_seconds
            and action.kind in obligation.allowed_actions
            and (obligation.bar is None or action.bar == obligation.bar)
        )
        return RotationTankDefensiveObligationAssessment(
            obligation_id=obligation.obligation_id,
            satisfied=len(matching) >= obligation.minimum_responses,
            matching_actions=matching,
            required_responses=obligation.minimum_responses,
            provenance=obligation.provenance,
        )

    def evaluate_candidate(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        obligations: tuple[RotationTankDefensiveObligation, ...],
    ) -> RotationCandidateRoleHardObligationEvidence:
        if not obligations:
            return RotationCandidateRoleHardObligationEvidence(
                candidate_id=candidate.candidate_id,
                satisfied=None,
                reasons=(
                    "tank defensive hard obligation unavailable: no explicit source-backed obligation supplied",
                ),
            )

        seen_ids: set[str] = set()
        assessments: list[RotationTankDefensiveObligationAssessment] = []
        for obligation in obligations:
            if obligation.obligation_id in seen_ids:
                raise ValueError(
                    f"duplicate tank defensive obligation id: {obligation.obligation_id}"
                )
            seen_ids.add(obligation.obligation_id)
            assessments.append(
                self.assess(plan=candidate.plan, obligation=obligation)
            )

        failed = [assessment for assessment in assessments if not assessment.satisfied]
        if failed:
            reasons = tuple(
                f"{assessment.obligation_id}: scheduled {len(assessment.matching_actions)} "
                f"of {assessment.required_responses} required defensive responses"
                for assessment in failed
            )
            return RotationCandidateRoleHardObligationEvidence(
                candidate_id=candidate.candidate_id,
                satisfied=False,
                reasons=reasons,
            )

        return RotationCandidateRoleHardObligationEvidence(
            candidate_id=candidate.candidate_id,
            satisfied=True,
            reasons=tuple(
                f"{assessment.obligation_id}: scheduled {len(assessment.matching_actions)} "
                f"defensive responses"
                for assessment in assessments
            ),
        )


__all__ = [
    "RotationTankDefensiveObligation",
    "RotationTankDefensiveObligationAssessment",
    "RotationTankDefensiveObligationService",
]
