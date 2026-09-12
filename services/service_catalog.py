from __future__ import annotations

"""Canonical discovery catalog for BFF architectural services.

The catalog is intentionally read-only metadata. It does not import, instantiate,
select, or execute implementations by string identity. Application code should
continue using normal typed imports and explicit dependency wiring.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ServiceLifecycle(str, Enum):
    PLANNED = "planned"
    PARTIAL = "partial"
    IMPLEMENTED = "implemented"
    DISABLED = "disabled"


class ServiceAuthority(str, Enum):
    CANONICAL = "canonical"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class ServiceBehavior(str, Enum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    CALIBRATED = "calibrated"
    HYBRID = "hybrid"


class EvidenceClass(str, Enum):
    GAME_MECHANIC = "game_mechanic"
    OBSERVATIONAL = "observational"
    CALIBRATION = "calibration"
    POLICY = "policy"
    MIXED = "mixed"
    NONE = "none"


class CapabilityStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    PLANNED = "planned"
    PARTIAL = "partial"
    IMPLEMENTED = "implemented"


class ServiceCatalogError(ValueError):
    """Base catalog metadata error."""


class ServiceCatalogAmbiguityError(ServiceCatalogError):
    """A supposedly unique service query matched more than one descriptor."""


@dataclass(frozen=True)
class ServiceDescriptor:
    """Stable architectural metadata for one BFF service responsibility."""

    service_id: str
    domain: str
    purpose: str
    implementation_path: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    lifecycle: ServiceLifecycle = ServiceLifecycle.IMPLEMENTED
    authority: ServiceAuthority = ServiceAuthority.CANONICAL
    behavior: ServiceBehavior = ServiceBehavior.DETERMINISTIC
    roles: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    ui_safe: bool = False
    encounter_aware: bool = False
    evidence_class: EvidenceClass = EvidenceClass.NONE
    provenance: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    superseded_by: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for field_name in ("service_id", "domain", "purpose", "implementation_path"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ServiceCatalogError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)

        object.__setattr__(self, "inputs", _clean_tuple(self.inputs))
        object.__setattr__(self, "outputs", _clean_tuple(self.outputs))
        object.__setattr__(self, "dependencies", _clean_tuple(self.dependencies))
        object.__setattr__(self, "roles", _clean_tuple(self.roles))
        object.__setattr__(self, "responsibilities", _clean_tuple(self.responsibilities))
        object.__setattr__(self, "provenance", _clean_tuple(self.provenance))
        object.__setattr__(self, "supersedes", _clean_tuple(self.supersedes))
        if self.superseded_by is not None:
            object.__setattr__(
                self,
                "superseded_by",
                str(self.superseded_by).strip() or None,
            )

    @property
    def available(self) -> bool:
        return (
            self.lifecycle in {ServiceLifecycle.PARTIAL, ServiceLifecycle.IMPLEMENTED}
            and self.authority is not ServiceAuthority.DEPRECATED
        )


def _clean_tuple(values: Iterable[str]) -> tuple[str, ...]:
    cleaned = tuple(str(value or "").strip() for value in values)
    if any(not value for value in cleaned):
        raise ServiceCatalogError("descriptor tuple values must be non-empty")
    return cleaned


class ServiceCatalog:
    """Read-only discovery and capability queries over explicit descriptors."""

    def __init__(self, descriptors: Iterable[ServiceDescriptor]) -> None:
        self._descriptors = tuple(descriptors)

    @property
    def descriptors(self) -> tuple[ServiceDescriptor, ...]:
        return self._descriptors

    def get(self, service_id: str) -> ServiceDescriptor | None:
        wanted = str(service_id or "").strip()
        matches = tuple(row for row in self._descriptors if row.service_id == wanted)
        if len(matches) > 1:
            raise ServiceCatalogAmbiguityError(f"duplicate service id: {wanted}")
        return matches[0] if matches else None

    def by_domain(
        self,
        domain: str,
        *,
        available_only: bool = False,
    ) -> tuple[ServiceDescriptor, ...]:
        wanted = str(domain or "").strip().casefold()
        rows = tuple(
            row for row in self._descriptors if row.domain.casefold() == wanted
        )
        if available_only:
            rows = tuple(row for row in rows if row.available)
        return rows

    def canonical_for(self, responsibility: str) -> ServiceDescriptor | None:
        wanted = str(responsibility or "").strip()
        matches = tuple(
            row
            for row in self._descriptors
            if wanted in row.responsibilities
            and row.authority is ServiceAuthority.CANONICAL
            and row.lifecycle is not ServiceLifecycle.DISABLED
        )
        if len(matches) > 1:
            ids = ", ".join(row.service_id for row in matches)
            raise ServiceCatalogAmbiguityError(
                f"multiple canonical services for {wanted}: {ids}"
            )
        return matches[0] if matches else None

    def capability_status(self, responsibility: str) -> CapabilityStatus:
        wanted = str(responsibility or "").strip()
        rows = tuple(
            row for row in self._descriptors if wanted in row.responsibilities
        )
        if not rows:
            return CapabilityStatus.UNAVAILABLE

        canonical = tuple(
            row
            for row in rows
            if row.authority is ServiceAuthority.CANONICAL
            and row.lifecycle is not ServiceLifecycle.DISABLED
        )
        considered = canonical or tuple(
            row for row in rows if row.authority is not ServiceAuthority.DEPRECATED
        )
        lifecycles = {row.lifecycle for row in considered}
        if ServiceLifecycle.IMPLEMENTED in lifecycles:
            return CapabilityStatus.IMPLEMENTED
        if ServiceLifecycle.PARTIAL in lifecycles:
            return CapabilityStatus.PARTIAL
        if ServiceLifecycle.PLANNED in lifecycles:
            return CapabilityStatus.PLANNED
        return CapabilityStatus.UNAVAILABLE

    def consuming(self, type_id: str) -> tuple[ServiceDescriptor, ...]:
        wanted = str(type_id or "").strip()
        return tuple(row for row in self._descriptors if wanted in row.inputs)

    def producing(self, type_id: str) -> tuple[ServiceDescriptor, ...]:
        wanted = str(type_id or "").strip()
        return tuple(row for row in self._descriptors if wanted in row.outputs)

    def dependencies_of(self, service_id: str) -> tuple[ServiceDescriptor, ...]:
        row = self.get(service_id)
        if row is None:
            return ()
        return tuple(
            dependency
            for dependency_id in row.dependencies
            if (dependency := self.get(dependency_id)) is not None
        )

    def dependents_of(self, service_id: str) -> tuple[ServiceDescriptor, ...]:
        wanted = str(service_id or "").strip()
        return tuple(row for row in self._descriptors if wanted in row.dependencies)


SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="encounter.projection",
        domain="encounter",
        purpose="Load and normalize canonical encounter definitions for deterministic consumers.",
        implementation_path="services.encounter_projection",
        inputs=("EncounterSource",),
        outputs=("EncounterDefinition",),
        responsibilities=("encounter_definition_projection",),
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="encounter.repository",
        domain="encounter",
        purpose="Provide deterministic read-only access to canonical encounter records.",
        implementation_path="services.encounter_repository",
        inputs=("EncounterId", "CanonicalEncounterData"),
        outputs=("EncounterDefinition",),
        dependencies=("encounter.projection",),
        responsibilities=("canonical_encounter_access",),
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="team.prescription.candidate_pool",
        domain="team",
        purpose="Group and gate pre-evaluated team prescription candidates by roster slot.",
        implementation_path="services.team_prescription_candidate_pool",
        inputs=("PrescribedRoster", "PrescribedCandidatePoolInput"),
        outputs=("PrescribedCandidatePoolResult",),
        responsibilities=("team_prescription_candidate_pooling",),
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.prescription.optimizer",
        domain="team",
        purpose="Select unique evidence-backed winners for prescribed roster slots.",
        implementation_path="services.team_prescription_optimizer",
        inputs=("PrescribedRoster", "PrescribedCandidatePoolResult"),
        outputs=("TeamPrescriptionOptimizationResult",),
        responsibilities=("team_prescription_candidate_optimization",),
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.prescription.candidate_source",
        domain="team",
        purpose="Evaluate explicit open-slot candidates into evidence used by prescription.",
        implementation_path="services.team_prescription_candidate_source",
        inputs=("PrescribedRoster", "PrescribedOpenSlotCandidate"),
        outputs=("PrescribedCandidateSourceResult",),
        responsibilities=("team_prescription_candidate_evidence",),
        evidence_class=EvidenceClass.MIXED,
    ),
    ServiceDescriptor(
        service_id="team.prescription.pipeline",
        domain="team",
        purpose="Run the canonical evidence-backed candidate portion of team prescription end to end.",
        implementation_path="services.team_prescription_pipeline",
        inputs=("PrescribedRoster", "PrescribedCandidatePoolInput"),
        outputs=("TeamPrescriptionPipelineResult",),
        dependencies=(
            "team.prescription.candidate_pool",
            "team.prescription.optimizer",
            "team.prescription.candidate_source",
        ),
        responsibilities=("team_prescription_pipeline",),
        ui_safe=True,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
    ),
    ServiceDescriptor(
        service_id="rotation.duration_refinement",
        domain="rotation",
        purpose="Refine rotation plans using canonical duration and demand scheduling rules.",
        implementation_path="services.rotation_duration_refinement_service",
        inputs=("RotationPlan", "AbilityPriorityList", "RotationDemandWindow"),
        outputs=("RotationRefinementResult",),
        responsibilities=("rotation_duration_refinement",),
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="rotation.candidate_generation",
        domain="rotation",
        purpose="Generate deterministic rotation-plan variants from explicit policy options.",
        implementation_path="services.rotation_candidate_generation_service",
        inputs=("RotationPlan", "AbilityPriorityList", "RotationDemandWindow"),
        outputs=("GeneratedRotationCandidate",),
        dependencies=("rotation.duration_refinement",),
        responsibilities=("rotation_candidate_generation",),
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="rotation.healer.canonical_role_output_factory",
        domain="rotation",
        purpose=(
            "Compose saved-build static contexts and explicit reviewed runtime evidence "
            "into canonical multi-demand healer role output."
        ),
        implementation_path=(
            "services.rotation_healer_canonical_role_output_factory_service"
        ),
        inputs=(
            "PlayerBuild",
            "RotationDemandWindow",
            "ReviewedHealerRuntimeEvidence",
            "ExplicitConditionalHealingAssumption",
        ),
        outputs=("RotationHealerCanonicalRoleOutputFactoryResult",),
        responsibilities=("rotation_healer_canonical_role_output_composition",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Encounter thresholds, target counts, raid DPS, and conditional attacker "
            "counts remain explicit caller policy."
        ),
    ),
    ServiceDescriptor(
        service_id="logs.esologs.composition_evidence",
        domain="logs",
        purpose="Aggregate observed ESO Logs team snapshots into composition evidence without treating popularity as canonical truth.",
        implementation_path="services.esologs_composition_evidence",
        inputs=("TopTeamResult",),
        outputs=("EsoLogsCompositionEvidence",),
        responsibilities=("esologs_composition_observation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("ESO Logs observed team snapshots",),
    ),
    ServiceDescriptor(
        service_id="logs.esologs.healer_sqlite_discovery",
        domain="logs",
        purpose="Inspect imported ESO Logs SQLite evidence and inventory fights, healer actors, and observed ability aliases.",
        implementation_path="services.rotation_healer_esologs_sqlite_discovery_service",
        inputs=("EsoLogsSqliteDatabase",),
        outputs=("RotationHealerEsoLogsSqliteDiscoveryReport",),
        responsibilities=("esologs_healer_observation_discovery",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("Imported ESO Logs event evidence",),
        notes="Observed numeric ability IDs are evidence only and do not establish canonical skill identity.",
    ),
    ServiceDescriptor(
        service_id="logs.esologs.canonical_skill_alias",
        domain="logs",
        purpose="Resolve numeric ESO Logs ability aliases from canonical lower-snake-case skill identity.",
        implementation_path="services.rotation_healer_esologs_canonical_skill_alias_service",
        inputs=("CanonicalSkillId", "CanonicalAbilityDatabase"),
        outputs=("RotationHealerEsoLogsCanonicalSkillAliases",),
        responsibilities=("esologs_canonical_skill_alias_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.MIXED,
        provenance=("Canonical ability.index_name", "ESO Logs numeric ability aliases"),
        notes="Canonical lower-snake-case skill IDs remain authoritative; numeric ESO ability IDs are aliases only.",
    ),
    ServiceDescriptor(
        service_id="calibration.btv.benchmark_evidence",
        domain="calibration",
        purpose="Load and validate scoped BTVTools screenshot benchmark observations and denominator provenance.",
        implementation_path="services.btv_benchmark_evidence_service",
        inputs=("BTVBenchmarkFixture",),
        outputs=("BTVBenchmarkCorpus",),
        responsibilities=("btv_benchmark_calibration_evidence",),
        behavior=ServiceBehavior.CALIBRATED,
        encounter_aware=True,
        evidence_class=EvidenceClass.CALIBRATION,
        provenance=("BTVTools screenshot observations",),
        notes="Calibration/reference evidence is not canonical ESO mechanic truth.",
    ),
    ServiceDescriptor(
        service_id="performance.dashboard",
        domain="performance",
        purpose="Build role-aware performance snapshots from ESO Logs actor, output, ability, and uptime observations.",
        implementation_path="services.performance_dashboard_service",
        inputs=("EsoLogsReport", "FightId", "ActorId", "Role"),
        outputs=("PerformanceSnapshot",),
        responsibilities=("performance_dashboard_snapshot",),
        behavior=ServiceBehavior.HYBRID,
        roles=("Tank", "Healer", "DPS"),
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("ESO Logs report observations",),
        notes="Dashboard calculations summarize observed log data and do not redefine canonical game mechanics.",
    ),
    ServiceDescriptor(
        service_id="team.provider.coverage",
        domain="team",
        purpose="Evaluate deterministic recipient-capacity coverage for team-facing provider mechanics.",
        implementation_path="services.team_provider_coverage_service",
        inputs=("TeamProviderCoverageProfile", "RequiredRecipients"),
        outputs=("TeamProviderCoverageResult",),
        responsibilities=("team_provider_recipient_coverage",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.provider.temporal_coverage",
        domain="team",
        purpose="Evaluate deterministic provider uptime over explicit encounter strategy windows.",
        implementation_path="services.team_provider_temporal_coverage_service",
        inputs=("TeamProviderTemporalRequirement", "TeamProviderTimedApplication"),
        outputs=("TeamProviderTemporalCoverageResult",),
        responsibilities=("team_provider_temporal_coverage",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.provider.rotation_workload",
        domain="team",
        purpose="Measure provider-plan workload dimensions without collapsing tradeoffs into one invented score.",
        implementation_path="services.team_provider_rotation_workload_service",
        inputs=("RotationPlan", "TeamProviderScheduledActionCost", "TeamProviderCoverageResult", "TeamProviderTemporalCoverageResult"),
        outputs=("TeamProviderRotationWorkload",),
        dependencies=("team.provider.coverage", "team.provider.temporal_coverage"),
        responsibilities=("team_provider_rotation_workload",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
    ),
    ServiceDescriptor(
        service_id="team.provider.canonical_workload",
        domain="team",
        purpose="Bridge saved builds and canonical ESO action evidence into team-provider workload projections.",
        implementation_path="services.team_provider_canonical_workload_service",
        inputs=("PlayerBuild", "CharacterProgression", "RotationPlan", "TeamProviderCoverageResult", "TeamProviderTemporalCoverageResult"),
        outputs=("TeamProviderCanonicalWorkloadProjection",),
        dependencies=(
            "team.provider.coverage",
            "team.provider.temporal_coverage",
            "team.provider.rotation_workload",
        ),
        responsibilities=("team_provider_canonical_workload_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Delegates canonical action cost, timing, and saved-build ownership to existing authoritative mechanics services.",
    ),
    ServiceDescriptor(
        service_id="team.provider.workload_candidate",
        domain="team",
        purpose="Bind explicit selected builds and scheduled provider actions into canonical workload candidates.",
        implementation_path="services.team_provider_workload_candidate_service",
        inputs=("PlayerBuild", "RotationPlan", "CharacterProgression", "TeamProviderWorkloadAlternativeRequest"),
        outputs=("TeamProviderWorkloadCandidateResult",),
        dependencies=(
            "team.provider.coverage",
            "team.provider.temporal_coverage",
            "team.provider.canonical_workload",
        ),
        responsibilities=("team_provider_workload_candidate_generation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Does not infer effects from skill names, roles, gear, or static capability availability.",
    ),
    ServiceDescriptor(
        service_id="team.provider.workload_frontier",
        domain="team",
        purpose="Remove only provider alternatives that are unambiguously dominated across comparable workload dimensions.",
        implementation_path="services.team_provider_workload_frontier_service",
        inputs=("TeamProviderRotationWorkload",),
        outputs=("TeamProviderWorkloadFrontierResult",),
        dependencies=("team.provider.rotation_workload",),
        responsibilities=("team_provider_workload_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.provider.workload_decision",
        domain="team",
        purpose="Classify projected provider alternatives as frontier, dominated, blocked, or rejected without inventing encounter policy.",
        implementation_path="services.team_provider_workload_decision_service",
        inputs=("TeamProviderWorkloadCandidateResult",),
        outputs=("TeamProviderWorkloadDecisionResult",),
        dependencies=(
            "team.provider.workload_candidate",
            "team.provider.workload_frontier",
        ),
        responsibilities=("team_provider_workload_decision",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="extreme.partial_named_gear_physical_feasibility",
        domain="extreme",
        purpose=(
            "Prove a necessary-condition physical legality gate for partial named-set "
            "assignments before full witness construction."
        ),
        implementation_path="services.extreme_partial_named_gear_physical_feasibility_service",
        inputs=("ExtremeGearSetCountTopology", "ExtremeNamedGearSetSlotEligibilityPrefix"),
        outputs=("ExtremePartialNamedGearPhysicalFeasibilityResult",),
        responsibilities=("partial_named_gear_physical_feasibility",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "A negative result proves the branch cannot become physically legal. "
            "A positive result is only permission to continue toward a full named-slot witness."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.healing_event",
        domain="extreme",
        purpose="Evaluate one healing event through canonical build and combat math.",
        implementation_path="services.extreme_healing_event_service",
        inputs=("PlayerBuild", "HealingEntityId"),
        outputs=("ExtremeHealingEventResult",),
        responsibilities=("extreme_healing_event_evaluation",),
        roles=("Healer",),
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_optimization",
        domain="extreme",
        purpose="Maximize an identified healing event through canonical whole-build evaluation.",
        implementation_path="services.extreme_actual_heal_optimization_service",
        inputs=("PlayerBuild", "HealingEntityId"),
        outputs=("ExtremeActualHealOptimizationResult",),
        dependencies=("extreme.healing_event",),
        responsibilities=("extreme_actual_heal_optimization",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Tooltip deltas may bound candidate discovery but are never final score. "
            "Observational calibration must remain distinct from canonical mechanics."
        ),
    ),
)

from services.comp_maker_catalog_descriptors import COMP_MAKER_SERVICE_DESCRIPTORS

SERVICE_DESCRIPTORS = (*SERVICE_DESCRIPTORS, *COMP_MAKER_SERVICE_DESCRIPTORS)
SERVICE_CATALOG = ServiceCatalog(SERVICE_DESCRIPTORS)


def get_service(service_id: str) -> ServiceDescriptor | None:
    return SERVICE_CATALOG.get(service_id)


def services_by_domain(
    domain: str,
    *,
    available_only: bool = False,
) -> tuple[ServiceDescriptor, ...]:
    return SERVICE_CATALOG.by_domain(domain, available_only=available_only)


def canonical_service_for(responsibility: str) -> ServiceDescriptor | None:
    return SERVICE_CATALOG.canonical_for(responsibility)


def capability_status(responsibility: str) -> CapabilityStatus:
    return SERVICE_CATALOG.capability_status(responsibility)


def services_consuming(type_id: str) -> tuple[ServiceDescriptor, ...]:
    return SERVICE_CATALOG.consuming(type_id)


def services_producing(type_id: str) -> tuple[ServiceDescriptor, ...]:
    return SERVICE_CATALOG.producing(type_id)
