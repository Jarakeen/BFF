from __future__ import annotations

from collections.abc import Mapping
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
from services.rotation_healer_canonical_delayed_timing_service import (
    RotationHealerCanonicalDelayedTimingService,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
    RotationHealerDelayedRuntimeProjection,
    RotationHealerDelayedRuntimeService,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
    RotationHealerDemandHealingEvidenceService,
    RotationHealerExternalConditionalDemandAssumption,
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
    """Compose existing healer mechanics into candidate-specific demand evidence."""

    def __init__(
        self,
        *,
        database_path: str | Path,
        build: PlayerBuild,
        context: BuildCalculationContext,
        contexts_by_bar: Mapping[str, BuildCalculationContext] | None = None,
        action_healing_service: RotationHealerActionHealingService | object | None = None,
        periodic_timing_service: (
            RotationHealerSavedBuildPeriodicTimingService | object | None
        ) = None,
        periodic_runtime_evidence_service: (
            RotationHealerPeriodicRuntimeEvidenceService | object | None
        ) = None,
        periodic_runtime_service: RotationHealerPeriodicRuntimeService | object | None = None,
        canonical_delayed_timing_service: (
            RotationHealerCanonicalDelayedTimingService | object | None
        ) = None,
        delayed_runtime_service: RotationHealerDelayedRuntimeService | object | None = None,
        demand_healing_service: (
            RotationHealerDemandHealingEvidenceService | object | None
        ) = None,
        budding_seeds_activation_service: (
            RotationHealerBuddingSeedsActivationService | object | None
        ) = None,
        reviewed_runtime_observations: tuple[RotationHealerReviewedRuntimeObservation, ...] = (),
        delayed_runtime_evidence: tuple[RotationHealerDelayedRuntimeEvidence, ...] = (),
        external_conditional_assumptions: tuple[
            RotationHealerExternalConditionalDemandAssumption, ...
        ] = (),
    ) -> None:
        path = Path(database_path)
        self.build = build
        self.context = context
        self.contexts_by_bar = self._normalize_contexts_by_bar(contexts_by_bar)
        self.action_healing_service = action_healing_service or RotationHealerActionHealingService(path)
        self.periodic_timing_service = periodic_timing_service or RotationHealerSavedBuildPeriodicTimingService(path)
        self.periodic_runtime_evidence_service = (
            periodic_runtime_evidence_service or RotationHealerPeriodicRuntimeEvidenceService()
        )
        self.periodic_runtime_service = periodic_runtime_service or RotationHealerPeriodicRuntimeService()
        self.canonical_delayed_timing_service = (
            canonical_delayed_timing_service or RotationHealerCanonicalDelayedTimingService(path)
        )
        self.delayed_runtime_service = delayed_runtime_service or RotationHealerDelayedRuntimeService()
        self.demand_healing_service = demand_healing_service or RotationHealerDemandHealingEvidenceService()
        self.budding_seeds_activation_service = (
            budding_seeds_activation_service or RotationHealerBuddingSeedsActivationService()
        )
        self.reviewed_runtime_observations = tuple(reviewed_runtime_observations)
        self.delayed_runtime_evidence = tuple(delayed_runtime_evidence)
        self.external_conditional_assumptions = tuple(
            external_conditional_assumptions
        )

    def evaluate_demand(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        demand: RotationDemandWindow,
    ) -> RotationHealerDemandHealingEvidence:
        if demand.kind is not RotationDemandKind.HEALING:
            raise ValueError("canonical healer demand evidence requires a healing demand window")

        action_kwargs = {
            "plan": candidate.plan,
            "build": self.build,
            "context": self.context,
        }
        if self.contexts_by_bar is not None:
            action_kwargs["contexts_by_bar"] = self.contexts_by_bar
        projection = self.action_healing_service.project(**action_kwargs)

        bridge_unresolved: list[str] = []
        delayed_runtime_evidence = tuple(self.delayed_runtime_evidence)
        if projection.delayed_seeds:
            delayed_runtime_evidence, delayed_unresolved = self._delayed_runtime_evidence(
                projection
            )
            bridge_unresolved.extend(delayed_unresolved)

        projection = self._apply_special_activation_topology(
            candidate=candidate,
            projection=projection,
            delayed_runtime_evidence=delayed_runtime_evidence,
        )

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
                evidence=delayed_runtime_evidence,
                horizon_seconds=candidate.plan.duration_seconds,
            )

        result = self.demand_healing_service.assess(
            demand=demand,
            projection=projection,
            periodic_projection=periodic_projection,
            delayed_projection=delayed_projection,
            external_conditional_assumptions=self.external_conditional_assumptions,
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
            modeled_external_conditional_healing=(
                result.modeled_external_conditional_healing
            ),
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

    def _delayed_runtime_evidence(
        self,
        projection: RotationHealerActionHealingProjection,
    ) -> tuple[tuple[RotationHealerDelayedRuntimeEvidence, ...], tuple[str, ...]]:
        explicit = {
            (item.source_name.casefold(), int(item.coefficient_number)): item
            for item in self.delayed_runtime_evidence
        }
        resolved = dict(explicit)
        unresolved: list[str] = []
        seen_keys: set[tuple[str, int]] = set()

        for seed in projection.delayed_seeds:
            key = (seed.source_name.casefold(), int(seed.coefficient_number))
            if key in seen_keys or key in resolved:
                seen_keys.add(key)
                continue
            seen_keys.add(key)

            resolution = self.canonical_delayed_timing_service.resolve(
                source_name=seed.source_name,
                coefficient_number=seed.coefficient_number,
            )
            unresolved.extend(tuple(getattr(resolution, "unresolved", ())))
            runtime_evidence = getattr(resolution, "runtime_evidence", None)
            if runtime_evidence is not None:
                resolved[key] = runtime_evidence

        return tuple(resolved.values()), self._dedupe(tuple(unresolved))

    def _apply_special_activation_topology(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        projection: RotationHealerActionHealingProjection,
        delayed_runtime_evidence: tuple[RotationHealerDelayedRuntimeEvidence, ...],
    ) -> RotationHealerActionHealingProjection:
        budding_evidence = next(
            (
                item
                for item in delayed_runtime_evidence
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
            external_conditional_seeds=projection.external_conditional_seeds,
        )

    @staticmethod
    def _normalize_contexts_by_bar(
        contexts_by_bar: Mapping[str, BuildCalculationContext] | None,
    ) -> dict[str, BuildCalculationContext] | None:
        if contexts_by_bar is None:
            return None
        result: dict[str, BuildCalculationContext] = {}
        for raw_bar, context in contexts_by_bar.items():
            bar = str(raw_bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("canonical healer context key must be front or back")
            if bar in result:
                raise ValueError(f"duplicate canonical healer context bar: {bar}")
            result[bar] = context
        return result

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(str(value).strip() for value in values if str(value).strip())
        )


class RotationCandidateHealerRoleOutputService:
    """Aggregate canonical demand-window healing into modeled healer output."""

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
