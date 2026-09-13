from __future__ import annotations

"""Compose periodic target-Health support over canonical skill damage.

The periodic bridge handles only its explicitly reviewed safe subset. Every other
skill action delegates unchanged to the existing canonical skill-damage evaluator.
This keeps target-Health timing support additive rather than creating a second DD
formula path.
"""

from minmax.rotation_plan import RotationAction
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_target_health_damage_bridge_service import (
    RotationCandidatePeriodicTargetHealthDamageBridgeService,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)


class RotationCandidateTargetHealthAwareSkillDamageService:
    """Prefer reviewed periodic target-Health damage; otherwise delegate canonically."""

    def __init__(
        self,
        *,
        base: RotationCandidateSkillDamageEvidenceService,
        periodic_target_health_bridge: RotationCandidatePeriodicTargetHealthDamageBridgeService,
    ) -> None:
        self.base = base
        self.periodic_target_health_bridge = periodic_target_health_bridge

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        reviewed = self.periodic_target_health_bridge.evaluate_if_supported(
            candidate=candidate,
            action=action,
        )
        if reviewed is not None:
            return reviewed
        return self.base.evaluate_action(candidate=candidate, action=action)


__all__ = ["RotationCandidateTargetHealthAwareSkillDamageService"]
