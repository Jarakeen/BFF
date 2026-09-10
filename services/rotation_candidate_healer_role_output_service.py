from __future__ import annotations

from typing import Protocol

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)


class RotationCandidateHealerDemandEvidenceProvider(Protocol):
    """Resolve canonical modeled healing for one candidate in one demand window."""

    def evaluate_demand(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        demand: RotationDemandWindow,
    ) -> RotationHealerDemandHealingEvidence: ...


class RotationCandidateHealerRoleOutputService:
    """Aggregate canonical demand-window healing into modeled healer output.

    This service owns no ESO healing math. Direct, periodic, delayed, crit, build,
    and runtime consequences remain owned by the canonical healer projection
    services supplying ``RotationHealerDemandHealingEvidence``. This adapter only
    turns one explicit encounter healing window into a comparable whole-candidate
    role-output measurement.

    The result is *modeled healing per demand-second*, not observed/received HPS.
    Existing healing evidence is intentionally pre-recipient and pre-overheal, so
    this service must not multiply by target count or claim that the value proves
    survival. Any unresolved upstream healing evidence keeps role output unknown.
    """

    def __init__(
        self,
        *,
        demand: RotationDemandWindow,
        demand_evidence_provider: RotationCandidateHealerDemandEvidenceProvider,
    ) -> None:
        if demand.kind is not RotationDemandKind.HEALING:
            raise ValueError("healer role output requires a healing demand window")
        self.demand = demand
        self.demand_evidence_provider = demand_evidence_provider

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleOutputEvidence:
        evidence = self.demand_evidence_provider.evaluate_demand(
            candidate=candidate,
            demand=self.demand,
        )
        if evidence.demand != self.demand:
            raise ValueError(
                "rotation healer demand evidence mismatch: provider returned a "
                "different demand window"
            )

        unresolved = tuple(evidence.unresolved)
        value = None
        if not unresolved:
            value = float(evidence.modeled_total_healing) / self.demand.duration_seconds

        return RotationCandidateRoleOutputEvidence(
            candidate_id=candidate.candidate_id,
            value=value,
            unresolved=unresolved,
        )


__all__ = [
    "RotationCandidateHealerDemandEvidenceProvider",
    "RotationCandidateHealerRoleOutputService",
]
