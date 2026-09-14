from __future__ import annotations

"""Assess one generated Tank plan against ordered encounter priority context.

This is a soft candidate-comparison layer. It consumes explicit RotationPlan target
identities and reviewed priority cues; it does not infer skill purpose from names,
create hard obligations, or invent timing windows. Missing explicit target identity
remains unresolved for that cue rather than receiving guessed credit.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.rotation_plan import RotationPlan
from services.rotation_tank_encounter_priority_context_service import (
    RotationTankEncounterPriorityCue,
)


def _key(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class RotationTankPriorityCueStatus(str, Enum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RotationTankPriorityCueAssessment:
    priority: int
    responsibility_id: str
    directive: str
    target_key: str
    actor_name: str | None
    status: RotationTankPriorityCueStatus
    matching_action_count: int
    first_matching_action_seconds: float | None
    reason: str


@dataclass(frozen=True)
class RotationTankPriorityCandidateAssessment:
    candidate_id: str
    cues: tuple[RotationTankPriorityCueAssessment, ...]

    @property
    def preference_key(self) -> tuple[object, ...]:
        """Lexicographic soft preference, highest reviewed priorities first.

        For each priority level, candidates with fewer unresolved/unsatisfied cues sort
        ahead of otherwise equivalent candidates. No weighted exchange rate between
        priorities is invented.
        """
        levels = sorted({row.priority for row in self.cues})
        result: list[object] = []
        for level in levels:
            rows = tuple(row for row in self.cues if row.priority == level)
            unresolved = sum(row.status is RotationTankPriorityCueStatus.UNRESOLVED for row in rows)
            unsatisfied = sum(row.status is RotationTankPriorityCueStatus.UNSATISFIED for row in rows)
            satisfied = sum(row.status is RotationTankPriorityCueStatus.SATISFIED for row in rows)
            result.extend((unresolved, unsatisfied, -satisfied))
        return tuple(result)

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(row.reason for row in self.cues)


class RotationTankPriorityCandidateAssessmentService:
    def assess(
        self,
        *,
        candidate_id: str,
        plan: RotationPlan,
        priority_context: tuple[RotationTankEncounterPriorityCue, ...],
    ) -> RotationTankPriorityCandidateAssessment:
        candidate_id = str(candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("Tank priority candidate assessment requires candidate_id")
        cues = tuple(priority_context)
        if not cues:
            return RotationTankPriorityCandidateAssessment(candidate_id=candidate_id, cues=())

        plan_targets = tuple(
            (_key(action.target_key), float(action.time_seconds))
            for action in plan.actions
            if action.target_key is not None and _key(action.target_key)
        )
        assessments: list[RotationTankPriorityCueAssessment] = []
        for cue in cues:
            accepted_targets = {_key(cue.target_key)}
            if cue.actor_name:
                accepted_targets.add(_key(cue.actor_name))
            accepted_targets.discard("")

            matches = tuple(
                timestamp
                for target, timestamp in plan_targets
                if target in accepted_targets
            )
            if matches:
                status = RotationTankPriorityCueStatus.SATISFIED
                first = min(matches)
                reason = (
                    f"Tank priority {cue.priority} {cue.directive}: explicit target action "
                    f"present ({len(matches)} action(s), first at {first:g}s)."
                )
            elif not plan_targets:
                status = RotationTankPriorityCueStatus.UNRESOLVED
                first = None
                reason = (
                    f"Tank priority {cue.priority} {cue.directive}: candidate plan has no "
                    "explicit target identities, so priority coverage is unresolved."
                )
            else:
                status = RotationTankPriorityCueStatus.UNSATISFIED
                first = None
                reason = (
                    f"Tank priority {cue.priority} {cue.directive}: no explicit scheduled "
                    f"action targets {cue.actor_name or cue.target_key}."
                )
            assessments.append(
                RotationTankPriorityCueAssessment(
                    priority=int(cue.priority),
                    responsibility_id=cue.responsibility_id,
                    directive=cue.directive,
                    target_key=cue.target_key,
                    actor_name=cue.actor_name,
                    status=status,
                    matching_action_count=len(matches),
                    first_matching_action_seconds=first,
                    reason=reason,
                )
            )

        return RotationTankPriorityCandidateAssessment(
            candidate_id=candidate_id,
            cues=tuple(
                sorted(
                    assessments,
                    key=lambda row: (
                        row.priority,
                        row.responsibility_id.casefold(),
                        (row.actor_name or "").casefold(),
                    ),
                )
            ),
        )


__all__ = [
    "RotationTankPriorityCandidateAssessment",
    "RotationTankPriorityCandidateAssessmentService",
    "RotationTankPriorityCueAssessment",
    "RotationTankPriorityCueStatus",
]
