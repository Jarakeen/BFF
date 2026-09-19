from __future__ import annotations

"""Conservative skill-package seeding for Phase 14 Comp Maker.

Skill plans are more personal and encounter-sensitive than gear. This service may seed an
empty planned-skills package from strong candidate evidence, but it never replaces or
merges an existing package. Per-slot/front-back reconciliation belongs to a future
slot-aware skill model.
"""

from dataclasses import dataclass

from models.comp_plan_state import CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate


_ALLOWED_SOURCES = frozenset({"saved_build", "reference_template"})


@dataclass(frozen=True)
class CompSkillSeedProposal:
    seat_id: str
    candidate_id: str
    candidate_name: str
    source_kind: str
    skills: tuple[str, ...]
    eligible: bool
    reason: str

    @property
    def skill_count(self) -> int:
        return len(self.skills)


class CompPlanSkillSeedService:
    """Seed empty planned skills without ever overwriting an existing skill plan."""

    @staticmethod
    def propose(
        *,
        state: CompPlanState,
        seat_id: str,
        candidate: CompBuildCandidate,
    ) -> CompSkillSeedProposal:
        if not isinstance(state, CompPlanState):
            raise TypeError("skill seeding requires CompPlanState")
        if not isinstance(candidate, CompBuildCandidate):
            raise TypeError("skill seeding requires CompBuildCandidate")

        chair = state.chair(seat_id)
        if chair is None:
            raise ValueError(f"unknown Comp chair: {seat_id}")

        skills = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in tuple(candidate.skills or ())
                if str(value or "").strip()
            )
        )

        if chair.is_locked("skills"):
            eligible = False
            reason = "Skills are locked for this chair."
        elif chair.planned_skills:
            eligible = False
            reason = (
                f"{len(chair.planned_skills)} planned skill(s) already exist; "
                "existing skills are preserved."
            )
        elif candidate.source_kind not in _ALLOWED_SOURCES:
            eligible = False
            reason = "This source is evidence-only and cannot seed a full skill package."
        elif not skills:
            eligible = False
            reason = "This candidate does not contain known skills."
        elif candidate.source_kind == "reference_template" and not candidate.complete_build:
            eligible = False
            reason = "This reference is incomplete, so its skills remain suggestions only."
        else:
            eligible = True
            reason = (
                f"Fill the empty skill plan with {len(skills)} known skill(s) from "
                f"{candidate.name}; existing skills will never be replaced."
            )

        return CompSkillSeedProposal(
            seat_id=chair.seat_id,
            candidate_id=candidate.candidate_id,
            candidate_name=candidate.name,
            source_kind=candidate.source_kind,
            skills=skills,
            eligible=eligible,
            reason=reason,
        )

    def apply(
        self,
        *,
        state: CompPlanState,
        seat_id: str,
        candidate: CompBuildCandidate,
        proposal: CompSkillSeedProposal | None = None,
    ) -> tuple[CompPlanState, CompSkillSeedProposal]:
        proposal = proposal or self.propose(
            state=state,
            seat_id=seat_id,
            candidate=candidate,
        )
        if not proposal.eligible:
            return state, proposal

        chair = state.chair(seat_id)
        if chair is None:
            raise ValueError(f"unknown Comp chair: {seat_id}")

        # Re-check the two destructive boundaries at application time.
        if chair.is_locked("skills") or chair.planned_skills:
            refreshed = self.propose(
                state=state,
                seat_id=seat_id,
                candidate=candidate,
            )
            return state, refreshed

        return (
            state.with_chair(chair.with_changes(planned_skills=proposal.skills)),
            proposal,
        )


__all__ = [
    "CompPlanSkillSeedService",
    "CompSkillSeedProposal",
]
