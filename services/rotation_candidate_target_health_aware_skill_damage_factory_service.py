from __future__ import annotations

"""Compose target-Health-aware skill damage only when authoritative inputs exist.

This factory is intentionally inert unless all required inputs are explicit:
reviewed periodic target-Health semantics, an exact runtime target snapshot resolver,
and a non-empty target identity.  Otherwise the already-built canonical skill damage
provider is returned unchanged.

The factory owns no ESO math.  It only composes the reviewed periodic target-Health
eligibility/bridge services over the existing canonical skill-damage evaluator.
"""

from collections.abc import Callable

from minmax.combat_state_snapshot import CombatStateSnapshot
from services.rotation_candidate_periodic_target_health_damage_bridge_service import (
    RotationCandidatePeriodicTargetHealthDamageBridgeService,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_candidate_target_health_aware_skill_damage_service import (
    RotationCandidateTargetHealthAwareSkillDamageService,
)
from services.rotation_periodic_target_health_eligibility_service import (
    RotationPeriodicTargetHealthEligibilityService,
)
from services.rotation_periodic_target_health_semantics_service import (
    RotationPeriodicTargetHealthSemantics,
    RotationPeriodicTargetHealthSemanticsService,
)


RotationRuntimeTargetSnapshotResolver = Callable[
    [float, int | None], CombatStateSnapshot | None
]


class RotationCandidateTargetHealthAwareSkillDamageFactoryService:
    """Wrap canonical skill damage with reviewed periodic target-Health support."""

    def __init__(
        self,
        *,
        semantics: tuple[RotationPeriodicTargetHealthSemantics, ...] = (),
        snapshot_resolver: RotationRuntimeTargetSnapshotResolver | None = None,
        target_identity: str | None = None,
    ) -> None:
        self.semantics = tuple(semantics)
        self.snapshot_resolver = snapshot_resolver
        self.target_identity = str(target_identity or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(
            self.semantics
            and self.snapshot_resolver is not None
            and self.target_identity
        )

    def wrap(
        self,
        base: RotationCandidateSkillDamageEvidenceService,
    ):
        if not self.enabled:
            return base

        semantics_service = RotationPeriodicTargetHealthSemanticsService(
            self.semantics,
        )
        eligibility = RotationPeriodicTargetHealthEligibilityService(
            semantics_service=semantics_service,
        )
        bridge = RotationCandidatePeriodicTargetHealthDamageBridgeService(
            base=base,
            target_health_eligibility=eligibility,
            snapshot_resolver=self.snapshot_resolver,
            target_identity=self.target_identity,
        )
        return RotationCandidateTargetHealthAwareSkillDamageService(
            base=base,
            periodic_target_health_bridge=bridge,
        )


__all__ = [
    "RotationCandidateTargetHealthAwareSkillDamageFactoryService",
    "RotationRuntimeTargetSnapshotResolver",
]
