from __future__ import annotations

from typing import Protocol

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class RotationUltimateSkillDamageDelegate(Protocol):
    """Existing canonical named-skill damage evaluator used by Ultimate actions."""

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence: ...


class RotationCandidateUltimateDamageEvidenceService:
    """Route one scheduled Ultimate through the canonical skill-damage authority.

    Ultimate is a distinct rotation action because scheduling, bar ownership, and
    Ultimate economy have their own contracts. Its coefficient-bearing damage is
    still canonical skill damage, so this adapter changes only the schedule action
    category presented to the existing skill evaluator. Canonical lower-snake-case
    identity, timestamp, sequence, bar, coefficients, crit, mitigation, target
    state, and unresolved evidence are preserved.

    Periodic Ultimate damage remains fail-closed until the shared periodic runtime
    projection can bind Ultimate parent casts. This adapter does not invent a
    second periodic scheduler or silently convert a full DoT tooltip into cast-time
    damage.
    """

    def __init__(
        self,
        *,
        skill_damage_delegate: RotationUltimateSkillDamageDelegate,
    ) -> None:
        self.skill_damage_delegate = skill_damage_delegate

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.ULTIMATE:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} is not an Ultimate action for Ultimate damage evaluation",
                ),
            )

        skill_action = RotationAction(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            kind=RotationActionKind.SKILL,
            name=action.name,
            bar=action.bar,
        )
        evidence = self.skill_damage_delegate.evaluate_action(
            candidate=candidate,
            action=skill_action,
        )
        if (
            evidence.time_seconds != action.time_seconds
            or evidence.sequence != action.sequence
        ):
            raise ValueError(
                "Ultimate damage delegate returned evidence for a different scheduled action: "
                f"expected ({action.time_seconds:g}s, {action.sequence}), "
                f"got ({evidence.time_seconds:g}s, {evidence.sequence})"
            )
        return evidence


__all__ = [
    "RotationCandidateUltimateDamageEvidenceService",
    "RotationUltimateSkillDamageDelegate",
]
