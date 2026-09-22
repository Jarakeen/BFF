from __future__ import annotations

"""Resolve finalized potion-timing evidence from canonical DD runtime mechanics."""

from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from services.extreme_sustained_dps_generated_finalized_potion_axis_adapter_service import (
    ExtremeSustainedDPSFinalizedPotionTimingEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchorResolver,
    RotationCandidatePeriodicDamageRuntimeProjectionService,
)
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationCandidatePeriodicDamageTimingEvidenceService,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)


PotionActivationAnchorResolverFactory = Callable[
    [GeneratedRotationCandidate],
    PeriodicDamageActivationAnchorResolver | None,
]
PotionAdditionalResourceEventTimeResolver = Callable[
    [GeneratedRotationCandidate],
    tuple[float, ...],
]


class ExtremeSustainedDPSFinalizedPotionTimingEvidenceService:
    """Compose authoritative finalized timing evidence without scheduling policy.

    Periodic tick timing reuses the reviewed DD semantics registry plus canonical
    periodic projection. Heavy Attack completion timing reuses the same verified
    scheduler-reservation bridge consumed by sustain/damage paths.

    Resource maximum/restoration events outside ordinary scheduled actions, fixed
    recovery ticks, and verified Heavy Attack completion remain explicit caller
    evidence. Setting additional_resource_event_denominator_proven True is therefore
    a real proof assertion: with no resolver it means the caller has proven there are
    no additional modeled resource-event timestamps for this search family.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        periodic_semantics_registry: (
            RotationDDPeriodicRuntimeSemanticsRegistryService | object | None
        ) = None,
        activation_anchor_resolver_factory: (
            PotionActivationAnchorResolverFactory | None
        ) = None,
        additional_resource_event_time_resolver: (
            PotionAdditionalResourceEventTimeResolver | None
        ) = None,
        additional_resource_event_denominator_proven: bool = False,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.periodic_semantics_registry = (
            periodic_semantics_registry
            or RotationDDPeriodicRuntimeSemanticsRegistryService()
        )
        self.activation_anchor_resolver_factory = activation_anchor_resolver_factory
        self.additional_resource_event_time_resolver = (
            additional_resource_event_time_resolver
        )
        self.additional_resource_event_denominator_proven = bool(
            additional_resource_event_denominator_proven
        )

    def __call__(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> ExtremeSustainedDPSFinalizedPotionTimingEvidence:
        activation_anchor_resolver = (
            None
            if self.activation_anchor_resolver_factory is None
            else self.activation_anchor_resolver_factory(candidate)
        )
        timing = RotationCandidatePeriodicDamageTimingEvidenceService(
            self.database_path
        )
        projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
            timing,
            activation_anchor_resolver=activation_anchor_resolver,
        ).project(
            plan=candidate.plan,
            semantics=tuple(self.periodic_semantics_registry.load()),
        )

        heavy = (
            RotationHeavySustainProjectionService
            .completion_evidence_from_verified_reservations(candidate.plan)
        )
        additional_times = (
            ()
            if self.additional_resource_event_time_resolver is None
            else tuple(self.additional_resource_event_time_resolver(candidate))
        )

        return ExtremeSustainedDPSFinalizedPotionTimingEvidence(
            periodic_projections=(projection,),
            heavy_attack_completion_evidence=tuple(heavy),
            additional_resource_event_times=tuple(additional_times),
            additional_resource_event_denominator_proven=(
                self.additional_resource_event_denominator_proven
            ),
            unresolved=tuple(projection.unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSFinalizedPotionTimingEvidenceService",
    "PotionActivationAnchorResolverFactory",
    "PotionAdditionalResourceEventTimeResolver",
]
