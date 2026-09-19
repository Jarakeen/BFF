from __future__ import annotations

"""Selected-chair Comp Maker proposal evaluation.

This service compares the current canonical CompPlanState with one explicit candidate
proposal. It never mutates the caller's state and never treats evidence confidence as
the existence of the raid plan itself.
"""

from dataclasses import dataclass
from pathlib import Path

from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_plan_health_service import CompPlanHealth, CompPlanHealthService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _same_identity(left: object, right: object) -> bool:
    a = _clean(left).casefold()
    b = _clean(right).casefold()
    return bool(a and b and a == b)


def _status_map(health: CompPlanHealth) -> dict[str, str]:
    return dict(health.coverage_status)


def _assignment_map(health: CompPlanHealth) -> dict[str, str]:
    return {
        row.effect_name: row.state
        for row in health.assignment_reviews
    }


_EVIDENCE_STATES = frozenset({"available", "conditional"})


@dataclass(frozen=True)
class CompCandidateProposal:
    seat_id: str
    candidate_id: str
    candidate_name: str
    source_kind: str
    source_name: str
    applicable: bool
    blocked_fields: tuple[str, ...]
    changed_fields: tuple[str, ...]
    gained_planned_required: tuple[str, ...]
    lost_planned_required: tuple[str, ...]
    gained_effect_evidence: tuple[str, ...]
    lost_effect_evidence: tuple[str, ...]
    assignment_proof_improved: tuple[str, ...]
    assignment_proof_regressed: tuple[str, ...]
    duplicates_added: tuple[str, ...]
    duplicates_removed: tuple[str, ...]
    candidate_score: float
    score_reasons: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def changes_anything(self) -> bool:
        return bool(self.changed_fields)


class CompCandidateAdviserService:
    """Evaluate one candidate against the exact state the Comp page will save."""

    def __init__(self, database_path: Path) -> None:
        self.health = CompPlanHealthService(database_path)

    @staticmethod
    def _proposal_changes(
        chair: CompChairState,
        candidate: CompBuildCandidate,
    ) -> tuple[dict[str, object], tuple[str, ...]]:
        changes: dict[str, object] = {}
        blocked: list[str] = []

        candidate_class = _clean(candidate.eso_class)
        current_class = _clean(chair.eso_class)
        if candidate_class and candidate_class.casefold() != current_class.casefold():
            if chair.is_locked("class"):
                blocked.append("class")
            else:
                changes["eso_class"] = candidate_class

        candidate_gear = tuple(candidate.gear_sets or ())
        if candidate_gear and candidate_gear != tuple(chair.planned_gear_sets or ()):
            if chair.is_locked("gear"):
                blocked.append("gear")
            else:
                changes["planned_gear_sets"] = candidate_gear

        candidate_mundus = _clean(candidate.mundus)
        current_mundus = _clean(chair.planned_mundus)
        if candidate_mundus and candidate_mundus.casefold() != current_mundus.casefold():
            if chair.is_locked("mundus"):
                blocked.append("mundus")
            else:
                changes["planned_mundus"] = candidate_mundus

        wants_saved_build_binding = candidate.source_kind == "saved_build"
        if (
            wants_saved_build_binding
            and candidate.name != _clean(chair.selected_build_name)
        ):
            if chair.is_locked("build"):
                blocked.append("build")
            else:
                changes["selected_build_name"] = candidate.name

        if changes:
            changes.update(
                build_source_kind=candidate.source_kind,
                build_source_name=candidate.source_name,
                build_source_url=candidate.source_url,
                candidate_id=candidate.candidate_id,
            )

        # Candidate skills remain evidence only until the deferred skill-evidence pass.
        return changes, tuple(dict.fromkeys(blocked))

    def apply(
        self,
        *,
        state: CompPlanState,
        seat_id: str,
        candidate: CompBuildCandidate,
        proposal: CompCandidateProposal | None = None,
    ) -> tuple[CompPlanState, CompCandidateProposal]:
        """Apply only unlocked proposal fields and reuse an already-rendered proposal."""
        if proposal is None:
            proposal = self.evaluate(
                state=state,
                seat_id=seat_id,
                candidate=candidate,
            )
        chair = state.chair(seat_id)
        if chair is None:
            raise ValueError(f"unknown Comp chair: {seat_id}")
        changes, _blocked = self._proposal_changes(chair, candidate)
        if not changes:
            return state, proposal
        return state.with_chair(chair.with_changes(**changes)), proposal

    def evaluate(
        self,
        *,
        state: CompPlanState,
        seat_id: str,
        candidate: CompBuildCandidate,
        current_health: CompPlanHealth | None = None,
    ) -> CompCandidateProposal:
        if not isinstance(state, CompPlanState):
            raise TypeError("Comp adviser requires CompPlanState")
        if not isinstance(candidate, CompBuildCandidate):
            raise TypeError("Comp adviser requires CompBuildCandidate")

        chair = state.chair(seat_id)
        if chair is None:
            raise ValueError(f"unknown Comp chair: {seat_id}")

        current_health = current_health or self.health.evaluate(state)
        changes, blocked = self._proposal_changes(chair, candidate)

        # Locks are sacred. A blocked proposal is still explainable, but the comparison
        # must not pretend the locked field changed.
        proposed_state = state
        if changes:
            proposed_state = state.with_chair(chair.with_changes(**changes))
        proposed_health = self.health.evaluate(proposed_state)

        current_planned = set(current_health.planned_required)
        proposed_planned = set(proposed_health.planned_required)
        gained_planned = tuple(
            name
            for name in proposed_health.required_effects
            if name in proposed_planned and name not in current_planned
        )
        lost_planned = tuple(
            name
            for name in current_health.required_effects
            if name in current_planned and name not in proposed_planned
        )

        current_status = _status_map(current_health)
        proposed_status = _status_map(proposed_health)
        effect_order = tuple(name for name, _status in proposed_health.coverage_status)
        gained_evidence = tuple(
            name
            for name in effect_order
            if proposed_status.get(name) in _EVIDENCE_STATES
            and current_status.get(name) not in _EVIDENCE_STATES
        )
        lost_evidence = tuple(
            name
            for name in effect_order
            if current_status.get(name) in _EVIDENCE_STATES
            and proposed_status.get(name) not in _EVIDENCE_STATES
        )

        current_assignment = _assignment_map(current_health)
        proposed_assignment = _assignment_map(proposed_health)
        proof_rank = {
            "gap": 0,
            "assigned_unproven": 1,
            "backup_only": 1,
            "unassigned_available": 2,
            "assigned_conditional": 3,
            "assigned_supported": 4,
        }
        improved = tuple(
            name
            for name in effect_order
            if proof_rank.get(proposed_assignment.get(name, "gap"), 0)
            > proof_rank.get(current_assignment.get(name, "gap"), 0)
        )
        regressed = tuple(
            name
            for name in effect_order
            if proof_rank.get(proposed_assignment.get(name, "gap"), 0)
            < proof_rank.get(current_assignment.get(name, "gap"), 0)
        )

        current_duplicates = set(current_health.duplicate_effects)
        proposed_duplicates = set(proposed_health.duplicate_effects)
        duplicates_added = tuple(
            name for name in effect_order
            if name in proposed_duplicates and name not in current_duplicates
        )
        duplicates_removed = tuple(
            name for name in effect_order
            if name in current_duplicates and name not in proposed_duplicates
        )

        return CompCandidateProposal(
            seat_id=chair.seat_id,
            candidate_id=candidate.candidate_id,
            candidate_name=candidate.name,
            source_kind=candidate.source_kind,
            source_name=candidate.source_name,
            applicable=bool(changes),
            blocked_fields=blocked,
            changed_fields=tuple(changes),
            gained_planned_required=gained_planned,
            lost_planned_required=lost_planned,
            gained_effect_evidence=gained_evidence,
            lost_effect_evidence=lost_evidence,
            assignment_proof_improved=improved,
            assignment_proof_regressed=regressed,
            duplicates_added=duplicates_added,
            duplicates_removed=duplicates_removed,
            candidate_score=float(candidate.score),
            score_reasons=tuple(candidate.score_reasons or ()),
            unresolved=tuple(candidate.unresolved or ()),
        )


__all__ = [
    "CompCandidateAdviserService",
    "CompCandidateProposal",
]
