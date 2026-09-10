from __future__ import annotations

from pathlib import Path
from typing import Protocol

from minmax.build_calculation_context import BuildCalculationContext
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerActionHealingService,
)
from services.rotation_healer_budding_seeds_activation_service import (
    RotationHealerBuddingSeedsActivationService,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
    RotationHealerDelayedRuntimeProjection,
    RotationHealerDelayedRuntimeService,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
    RotationHealerDemandHealingEvidenceService,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRuntimeEvidenceService,
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeProjection,
    RotationHealerPeriodicRuntimeService,
)
from services.rotation_healer_saved_build_periodic_timing_service import (
    RotationHealerSavedBuildPeriodicTimingService,
)


class RotationCandidateHealerDemandEvidenceProvider(Protocol):
    """Resolve canonical modeled healing for one candidate in one demand window."""

    def evaluate_demand(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        demand: RotationDemandWindow,
    ) -> RotationHealerDemandHealingEvidence: ...


class RotationCandidateHealerCanonicalDemandEvidenceProvider:
    """Compose existing healer mechanics into candidate-specific demand evidence.

    This is orchestration only. Action healing, periodic cadence/duration, reviewed
    runtime facts, delayed timing, Budding Seeds activation topology, and demand
    filtering remain owned by their existing services. The provider never invents
    a tick cadence, refresh rule, delayed offset, target multiplier, or survival
    threshold. Missing runtime facts remain explicit unresolved evidence.
    """

    def __init__(
        self,
        *,
        database_path: str | Path,
        build: PlayerBuild,
        context: BuildCalculationContext,
        action_healing_service: RotationHealerActionHealingService | object | None = None,
        periodic_timing_service: (
            RotationHealerSavedBuildPeriodicTimingService | object | None
        ) = None,
        periodic_runtime_evidence_service: (
            RotationHealerPeriodicRuntimeEvidenceService | object | None
        ) = None,
        periodic_runtime_service: RotationHealerPeriodicRuntimeService | object | None = None,
        delayed_runtime_service: RotationHealerDelayedRuntimeService | object | None = None,
        demand_healing_service: (
            RotationHealerDemandHealingEvidenceService | object | None
        ) = None,
        budding_seeds_activation_service: (
            RotationHealerBuddingSeedsActivationService | object | None
        ) = None,
        reviewed_runtime_observations: tuple[RotationHealerReviewedRuntimeObservation, ...] = (),
        delayed_runtime_evidence: tuple[RotationHealerDelayedRuntimeEvidence, ...] = (),
    ) -> None:
        path = Path(database_path)
        self.build = build
        self.context = context
        self.action_healing_service = action_healing_service or RotationHealerActionHealingService(path)
        self.periodic_timing_service = periodic_timing_service or RotationHealerSavedBuildPeriodicTimingService(path)
        self.periodic_runtime_evidence_service = (
            periodic_runtime_evidence_service or RotationHealerPeriodicRuntimeEvidenceService()
        )
        self.periodic_runtime_service = periodic_runtime_service or RotationHealerPeriodicRuntimeService()
        self.delayed_runtime_service = delayed_runtime_service or RotationHealerDelayedRuntimeService()
        self.demand_healing_service = demand_healing_service or RotationHealerDemandHealingEvidenceService()
        self.budding_seeds_activation_service = (
            budding_seeds_activation_service or RotationHealerBuddingSeedsActivationService()
        )
        self.reviewed_runtime_observations = tuple(reviewed_runtime_observations)
        self.delayed_runtime_evidence = tuple(delayed_runtime_evidence)

    def evaluate_demand(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        demand: RotationDemandWindow,
    ) -> RotationHealerDemandHealingEvidence:
        if demand.kind is not RotationDemandKind.HEALING:
            raise ValueError("canonical healer demand evidence requires a healing demand window")

        projection = self.action_healing_service.project(
            plan=candidate.plan,
            build=self.build,
            context=self.context,
        )
        projection = self._apply_special_activation_topology(
            candidate=candidate,
            projection=projection,
        )

        bridge_unresolved: list[str] = []
        periodic_runtime_evidence = ()
        if projection.periodic_seeds:
            periodic_runtime_evidence, timing_unresolved = self._periodic_runtime_evidence(
                projection
            )
            bridge_unresolved.extend(timing_unresolved)

        periodic_projection = RotationHealerPeriodicRuntimeProjection(events=(), unresolved=())
        if projection.periodic_seeds:
            periodic_projection = self.periodic_runtime_service.project(
                seeds=projection.periodic_seeds,
                evidence=periodic_runtime_evidence,
                horizon_seconds=candidate.plan.duration_seconds,
            )

        delayed_projection = RotationHealerDelayedRuntimeProjection(events=(), unresolved=())
        if projection.delayed_seeds:
            delayed_projection = self.delayed_runtime_service.project(
                seeds=projection.delayed_seeds,
                evidence=self.delayed_runtime_evidence,
                horizon_seconds=candidate.plan.duration_seconds,
            )

        result = self.demand_healing_service.assess(
            demand=demand,
            projection=projection,
            periodic_projection=periodic_projection,
            delayed_projection=delayed_projection,
        )
        unresolved = self._dedupe(tuple(bridge_unresolved) + tuple(result.unresolved))
        if unresolved == result.unresolved:
            return result
        return RotationHealerDemandHealingEvidence(
            demand=result.demand,
            direct_events=result.direct_events,
            periodic_events=result.periodic_events,
            delayed_events=result.delayed_events,
            modeled_direct_healing=result.modeled_direct_healing,
            modeled_periodic_healing=result.modeled_periodic_healing,
            modeled_delayed_healing=result.modeled_delayed_healing,
            unresolved=unresolved,
        )

    def _periodic_runtime_evidence(
        self,
        projection: RotationHealerActionHealingProjection,
    ) -> tuple[tuple[object, ...], tuple[str, ...]]:
        report = self.periodic_timing_service.inspect(self.build)
        unresolved: list[str] = list(report.unresolved)
        entries_by_key: dict[tuple[str, int], list[object]] = {}
        for entry in report.entries:
            entries_by_key.setdefault(
                (entry.skill_name.casefold(), int(entry.coefficient_number)), []
            ).append(entry)

        observations = {
            (item.source_name.casefold(), int(item.coefficient_number)): item
            for item in self.reviewed_runtime_observations
        }
        seeds_by_key: dict[tuple[str, int], list[object]] = {}
        for seed in projection.periodic_seeds:
            seeds_by_key.setdefault(
                (seed.source_name.casefold(), int(seed.coefficient_number)), []
            ).append(seed)

        runtime: list[object] = []
        for key, seeds in seeds_by_key.items():
            entries = entries_by_key.get(key, [])
            if not entries:
                label = seeds[0]
                unresolved.append(
                    f"{label.source_name} coefficient {label.coefficient_number}: "
                    "saved-build periodic timing evidence unavailable"
                )
                continue

            canonical = entries[0].timing
            if any(entry.timing != canonical for entry in entries[1:]):
                label = seeds[0]
                unresolved.append(
                    f"{label.source_name} coefficient {label.coefficient_number}: "
                    "saved-build periodic timing evidence is ambiguous across slots"
                )
                continue

            resolution = self.periodic_runtime_evidence_service.resolve(
                canonical=canonical,
                observation=observations.get(key),
                repeated_applications=len(seeds) > 1,
            )
            unresolved.extend(resolution.unresolved)
            if resolution.runtime_evidence is not None:
                runtime.append(resolution.runtime_evidence)

        return tuple(runtime), self._dedupe(tuple(unresolved))

    def _apply_special_activation_topology(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        projection: RotationHealerActionHealingProjection,
    ) -> RotationHealerActionHealingProjection:
        budding_evidence = next(
            (
                item
                for item in self.delayed_runtime_evidence
                if item.source_name.casefold() == "budding seeds"
                and item.coefficient_number == 1
            ),
            None,
        )
        if budding_evidence is None:
            return projection
        if not any(
            seed.source_name.casefold() == "budding seeds"
            for seed in projection.delayed_seeds
        ):
            return projection

        activation = self.budding_seeds_activation_service.project(
            plan=candidate.plan,
            healing=projection,
            delayed_evidence=budding_evidence,
        )
        return RotationHealerActionHealingProjection(
            direct_events=tuple(projection.direct_events) + tuple(activation.special_events),
            periodic_seeds=activation.periodic_seeds,
            delayed_seeds=activation.delayed_seeds,
            unresolved=self._dedupe(tuple(projection.unresolved) + tuple(activation.unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(str(value).strip() for value in values if str(value).strip())
        )


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
    "RotationCandidateHealerCanonicalDemandEvidenceProvider",
    "RotationCandidateHealerDemandEvidenceProvider",
    "RotationCandidateHealerRoleOutputService",
]
