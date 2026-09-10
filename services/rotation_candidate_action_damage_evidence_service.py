from __future__ import annotations

from typing import Protocol

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class RotationActionDamageProvider(Protocol):
    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence: ...


class RotationCandidateActionDamageEvidenceService:
    """Route each scheduled damage action to its dedicated canonical evaluator.

    This is composition only. It owns no ESO damage formulas and does not turn a
    missing evaluator into zero damage. The whole-plan DD aggregator can therefore
    consume one provider while skill, light-attack, heavy-attack, and Ultimate
    mechanics remain independently owned.
    """

    def __init__(
        self,
        *,
        skill_provider: RotationActionDamageProvider | None = None,
        light_attack_provider: RotationActionDamageProvider | None = None,
        heavy_attack_provider: RotationActionDamageProvider | None = None,
        ultimate_provider: RotationActionDamageProvider | None = None,
    ) -> None:
        self._providers = {
            RotationActionKind.SKILL: skill_provider,
            RotationActionKind.LIGHT_ATTACK: light_attack_provider,
            RotationActionKind.HEAVY_ATTACK: heavy_attack_provider,
            RotationActionKind.ULTIMATE: ultimate_provider,
        }

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        provider = self._providers.get(action.kind)
        if provider is not None:
            return provider.evaluate_action(candidate=candidate, action=action)

        if action.kind in self._providers:
            reason = (
                f"{action.kind.value} damage consequence has no canonical evaluator configured"
            )
        else:
            reason = f"{action.kind.value} is not a routed rotation damage action"
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=(reason,),
        )


__all__ = [
    "RotationActionDamageProvider",
    "RotationCandidateActionDamageEvidenceService",
]
