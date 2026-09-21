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
        service_id="research.ultimate_source_reference_frontier",
        domain="research",
        purpose=(
            "Discover and route-classify Ultimate-generation candidates from a "
            "versioned reference snapshot without promoting them to canonical math."
        ),
        implementation_path="services.ultimate_source_reference_frontier_service",
        inputs=("UltimateCalculatorReferenceHtml",),
        outputs=("UltimateSourceReference",),
        responsibilities=("ultimate_generation_source_denominator_discovery",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("math/ESO Ultimate Generation Calculator _ U50 _ Hyperioxes.htm",),
        notes=(
            "Displayed rates are discovery evidence only; exact game tooltips, "
            "targeting, timing, and build legality remain separate proof obligations."
        ),
    ),
    ServiceDescriptor(
        service_id="mechanics.ultimate_source_runtime_legality",
        domain="mechanics",
        purpose=(
            "Apply exact recipient, cast, cadence, and route-legality review to "
            "Ultimate-generation candidates."
        ),
        implementation_path="services.ultimate_source_runtime_legality_service",
        inputs=("UltimateSourceId", "CanonicalSourceRecord", "UltimateTriggerWitness"),
        outputs=("UltimateSourceRuntimeReview",),
        responsibilities=("ultimate_source_runtime_legality",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Equipment, Vampire, and weapon-trait mutations remain explicit search "
            "states until whole-build scoring proves them."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.health_recovery_runtime_compatibility",
        domain="extreme",
        purpose=(
            "Prove whether dominant Health Recovery class, Champion Point, and gear "
            "conditions can coexist at one scoring moment."
        ),
        implementation_path=(
            "services.extreme_health_recovery_runtime_compatibility_service"
        ),
        inputs=(
            "ExtremeHealthRecoveryRuntimeState",
            "ChampionPointLoadoutCandidate",
            "ExtremeRecoverySpecialBranch",
        ),
        outputs=(
            "ExtremeHealthRecoveryChampionPointCompatibility",
            "ExtremeHealthRecoveryBranchCompatibility",
        ),
        responsibilities=("health_recovery_runtime_compatibility",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Runtime proof remains separate from legal CP loadout and numeric equipment scoring."
        ),
    ),
    ServiceDescriptor(
        service_id="mechanics.champion_point_loadout",
        domain="mechanics",
        purpose=(
            "Prove additive Champion Bar legality under the canonical four-slot "
            "limit for each discipline."
        ),
        implementation_path="services.champion_point_loadout_service",
        inputs=("ChampionPointLoadoutCandidate",),
        outputs=("ChampionPointLoadoutResult",),
        responsibilities=("champion_point_loadout_legality",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Runtime conditions remain evidence on selected candidates and are not "
            "made true by structural slot legality."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.health_recovery_champion_point_branch",
        domain="extreme",
        purpose=(
            "Classify and bound one Health Recovery Champion Point mechanic while "
            "preserving its runtime condition and deferring legal loadout composition."
        ),
        implementation_path=(
            "services.extreme_health_recovery_champion_point_branch_service"
        ),
        inputs=("ChampionPointRecord",),
        outputs=("ExtremeHealthRecoveryChampionPointBranch",),
        responsibilities=("health_recovery_champion_point_branch_classification",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Individual-star ceilings are not proof that multiple slottable stars can coexist."
        ),
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
        service_id="combat.simulation.kernel",
        domain="combat",
        purpose=(
            "Replay one exact EffectiveBuildSnapshot + RotationPlan into a deterministic "
            "event stream while preserving unresolved consequence evidence."
        ),
        implementation_path="services.combat_simulation_service",
        inputs=(
            "EffectiveBuildSnapshot",
            "RotationPlan",
            "CombatSimulationTargetState",
            "CombatSimulationIncomingDamage",
            "CombatSimulationOutgoingDamage",
        ),
        outputs=("CombatSimulationResult",),
        responsibilities=("combat_simulation_deterministic_execution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The kernel orchestrates canonical consequence services; it does not invent "
            "damage, healing, sustain, proc, targeting, or encounter mechanics."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.saved_rotation",
        domain="extreme",
        purpose=(
            "Evaluate one saved DD build and its canonical saved RotationPlan through "
            "Combat Simulation against explicit target Health/resistance assumptions."
        ),
        implementation_path="services.extreme_saved_rotation_combat_record_service",
        inputs=(
            "PlayerBuild",
            "RotationPlan",
            "TargetHealth",
            "TargetResistance",
        ),
        outputs=("ExtremeSavedRotationSustainedDPSResult",),
        dependencies=(
            "simulation.saved_build_dd",
            "simulation.damage_summary",
        ),
        responsibilities=("extreme_saved_rotation_sustained_dps_record",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Produces a constructive saved-build lower bound only. Global Extreme search "
            "across alternate legal builds and rotations remains a separate optimization responsibility."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.comparison",
        domain="extreme",
        purpose=(
            "Compare explicitly supplied saved DD build/rotation witnesses under one "
            "shared target scenario without promoting incomplete or incomparable evidence "
            "to a winner."
        ),
        implementation_path="services.extreme_sustained_dps_comparison_service",
        inputs=(
            "PlayerBuildCandidates",
            "TargetHealth",
            "TargetResistance",
        ),
        outputs=("ExtremeSustainedDPSComparisonResult",),
        dependencies=("extreme.sustained_dps.saved_rotation",),
        responsibilities=("extreme_sustained_dps_candidate_comparison",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "May identify a unique leader only within the explicitly supplied comparable "
            "candidate set. It does not prove the global Extreme maximum or search unsupplied builds."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.discovery",
        domain="extreme",
        purpose=(
            "Discover the canonical saved DD/DPS build denominator that has stable "
            "build identity and valid saved RotationPlan evidence."
        ),
        implementation_path="services.extreme_sustained_dps_candidate_discovery_service",
        inputs=("CanonicalSavedBuildLibrary", "SavedRotationArtifacts"),
        outputs=("ExtremeSustainedDPSDiscoveryResult",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_candidate_discovery",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Discovery does not synthesize builds or infer DD role from gear. "
            "Every excluded saved row remains visible with a reason."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.saved_state_search",
        domain="extreme",
        purpose=(
            "Search the complete eligible canonical saved DD/DPS denominator by "
            "discovering candidates and comparing every saved build/rotation witness "
            "under one explicit target scenario."
        ),
        implementation_path="services.extreme_sustained_dps_search_service",
        inputs=("CanonicalSavedBuildLibrary", "TargetHealth", "TargetResistance"),
        outputs=("ExtremeSustainedDPSSearchResult",),
        dependencies=(
            "extreme.sustained_dps.discovery",
            "extreme.sustained_dps.comparison",
        ),
        responsibilities=("extreme_sustained_dps_saved_state_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Complete only for the eligible saved user-state denominator. It does not "
            "generate unsaved builds/rotations or prove the theoretical ESO-wide maximum."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_frontier",
        domain="extreme",
        purpose=(
            "Enumerate the finite structural candidate frontier for generated sustained-DPS "
            "search from the canonical Extreme global universe without fabricating deferred "
            "dynamic build axes."
        ),
        implementation_path="services.extreme_sustained_dps_generated_candidate_service",
        inputs=("ExtremeGlobalSearchUniverse",),
        outputs=("ExtremeSustainedDPSGeneratedFrontier", "ExtremeSustainedDPSStructuralCandidate"),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_generated_structural_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Expands race, legal class route, 64-point attributes, and active bar only. "
            "Gear, traits, glyphs, Mundus, consumables, skills, CP, passives, and runtime "
            "rotation state remain explicit deferred axes until their own generators close them."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.dynamic_axes",
        domain="extreme",
        purpose=(
            "Inventory canonical dynamic refinement choices around one generated structural "
            "sustained-DPS candidate without promoting static character-sheet choices into "
            "an unsupported DPS upper bound."
        ),
        implementation_path="services.extreme_sustained_dps_dynamic_axis_inventory_service",
        inputs=("ExtremeSustainedDPSStructuralCandidate",),
        outputs=("ExtremeSustainedDPSDynamicAxisInventory",),
        dependencies=("extreme.sustained_dps.generated_frontier",),
        responsibilities=("extreme_sustained_dps_dynamic_axis_inventory",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Enumerates only canonical currently supported refinement axes. Sustained-DPS "
            "pruning remains fail-open until a proven optimistic action/rotation ceiling exists."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.armor_trait_enchant_frontier",
        domain="extreme",
        purpose=(
            "Count and page the complete modeled armor trait/enchant product for the actually "
            "equipped armor slots without materializing the full Cartesian product."
        ),
        implementation_path="services.extreme_sustained_dps_armor_trait_enchant_frontier_service",
        inputs=("PlayerBuild",),
        outputs=("ExtremeSustainedDPSArmorTraitEnchantFrontier",),
        dependencies=("extreme.sustained_dps.dynamic_axes",),
        responsibilities=("extreme_sustained_dps_armor_trait_enchant_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Preserves the full modeled denominator lazily and makes no DPS-specific trait/glyph "
            "dominance assumption. Enchant mutation is limited to slots already at the canonical "
            "CP160 + Truly Superb static resolver boundary."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.execute_policy_frontier",
        domain="extreme",
        purpose=(
            "Preserve baseline and canonical execute-upgrade rotation variants using "
            "reviewed execute opportunity, runtime threshold, exact-slot damage comparison, "
            "and mutation services."
        ),
        implementation_path="services.extreme_sustained_dps_execute_policy_frontier_service",
        inputs=(
            "GeneratedRotationCandidate",
            "AbilityPriorityList",
            "ExecuteSnapshotResolver",
            "TargetIdentity",
            "DurationRules",
        ),
        outputs=("ExtremeSustainedDPSExecutePolicyFrontier",),
        dependencies=("extreme.sustained_dps.rotation_policy_frontier",),
        responsibilities=("extreme_sustained_dps_execute_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Does not infer execute superiority. Canonical execute services decide whether "
            "runtime threshold evidence exists and whether exact-slot execute damage is strictly greater. "
            "The baseline remains a separate candidate."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.heavy_attack_policy_frontier",
        domain="extreme",
        purpose=(
            "Enumerate all compatible subsets of explicit caller-proven safe fully charged "
            "1.8-second Heavy Attack windows over one generated rotation candidate."
        ),
        implementation_path="services.extreme_sustained_dps_heavy_attack_policy_frontier_service",
        inputs=("GeneratedRotationCandidate", "ExplicitHeavyAttackWindows"),
        outputs=("ExtremeSustainedDPSHeavyAttackPolicyFrontier",),
        dependencies=("extreme.sustained_dps.rotation_policy_frontier",),
        responsibilities=("extreme_sustained_dps_heavy_attack_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Only exact ordinary skill slots in non-overlapping caller-proven safe 1.8s windows "
            "are mutated. Same-timestamp Light Attacks are removed, canonical reservation provenance "
            "is recorded, and shared full-charge completion evidence must promote every selected heavy. "
            "Damage remains owned by RotationCandidateHeavyAttackDamageEvidenceService."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.rotation_policy_frontier",
        domain="extreme",
        purpose=(
            "Enumerate explicit Ultimate-bar choice/as-soon-as-affordable policies and "
            "anchored potion first-use/reuse timing over one generated seed RotationPlan."
        ),
        implementation_path="services.extreme_sustained_dps_rotation_policy_frontier_service",
        inputs=(
            "PlayerBuild",
            "ExtremeSustainedDPSRotationPlanCandidate",
            "EffectivePotionCooldownSeconds",
            "StartingUltimate",
            "ExplicitUltimateGenerationEvidence",
        ),
        outputs=(
            "ExtremeSustainedDPSRotationPolicyFrontier",
            "ExtremeSustainedDPSRotationPolicyCandidate",
        ),
        dependencies=("extreme.sustained_dps.rotation_plan_frontier",),
        responsibilities=("extreme_sustained_dps_rotation_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Ultimate affordability/spend remains owned by RotationUltimateService and final "
            "Ultimate/potion legality remains owned by RotationScheduledActionResourceLegalityService. "
            "This frontier proves only its anchored potion family and explicit Ultimate-choice family; "
            "continuous potion offsets and deliberate post-affordability Ultimate delays remain open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.rotation_plan_frontier",
        domain="extreme",
        purpose=(
            "Lazily enumerate proof-neutral semi-static RotationPlan seed/cadence families "
            "for one coherent generated sustained-DPS candidate."
        ),
        implementation_path="services.extreme_sustained_dps_rotation_plan_frontier_service",
        inputs=("ExtremeSustainedDPSAssembledCandidate", "ExplicitDurationSeconds"),
        outputs=("ExtremeSustainedDPSRotationFamilyFrontier", "ExtremeSustainedDPSRotationPlanCandidate"),
        dependencies=("extreme.sustained_dps.generated_candidate_assembly",),
        responsibilities=("extreme_sustained_dps_rotation_plan_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Preserves every ordinary-skill ordering per populated bar, both legal start-bar "
            "routes when two bars are populated, and Light-Attack weave on/off. Canonical "
            "SemiStaticRotationPlanner builds each plan and duration refinement may be applied. "
            "Ultimate, potion, execute, Heavy Attack, encounter-demand, and broader policy "
            "families remain separate open axes."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.cross_axis_context",
        domain="extreme",
        purpose=(
            "Bind one generated build/progression/dual-bar gear witness into coherent "
            "class-route, explicit ownership, equipped weapon/armor, transformation, "
            "scribed-skill, and bar-access legality contexts."
        ),
        implementation_path="services.extreme_sustained_dps_cross_axis_context_service",
        inputs=("PlayerBuild", "CharacterProgression", "ExtremeDualBarGearState"),
        outputs=("ExtremeSustainedDPSCrossAxisContext",),
        dependencies=("extreme.sustained_dps.dual_bar_gear_frontier",),
        responsibilities=("extreme_sustained_dps_cross_axis_context",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Keeps native/equipped/explicitly-owned line evidence distinct, carries legal "
            "subclass route lines explicitly, and binds Oakensoul bar access before skill search. "
            "Configured scribed skills fail closed until canonical ability-ID mapping exists."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_candidate_assembly",
        domain="extreme",
        purpose=(
            "Assemble one coherent generated refinement candidate by applying CP, potion, "
            "passive-rank, and two-bar skill states onto the cross-axis-authoritative build."
        ),
        implementation_path="services.extreme_sustained_dps_generated_candidate_assembly_service",
        inputs=(
            "ExtremeSustainedDPSCrossAxisContext",
            "ChampionPointCandidate",
            "PotionCandidate",
            "PassiveRankCandidate",
            "SkillBarCandidate",
        ),
        outputs=("ExtremeSustainedDPSAssembledCandidate",),
        dependencies=(
            "extreme.sustained_dps.cross_axis_context",
            "extreme.sustained_dps.champion_point_frontier",
            "extreme.sustained_dps.potion_frontier",
            "extreme.sustained_dps.passive_rank_frontier",
            "extreme.sustained_dps.skill_bar_frontier",
        ),
        responsibilities=("extreme_sustained_dps_generated_candidate_assembly",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Each axis contributes only the state it owns; stale convenience build snapshots "
            "from other frontiers cannot overwrite gear/class/identity state. One-bar and "
            "explicit ownership invariants fail closed."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.skill_bar_frontier",
        domain="extreme",
        purpose=(
            "Count and page the legal generated front/back active-skill denominator while "
            "preserving base/morph alternatives and explicit skill-line ownership."
        ),
        implementation_path="services.extreme_sustained_dps_skill_bar_frontier_service",
        inputs=("PlayerBuild", "FrontSkillLegalityContext", "BackSkillLegalityContext"),
        outputs=("ExtremeSustainedDPSSkillBarFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_skill_bar_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Preserves empty slots, base/morph alternatives, one-family-per-bar legality, "
            "front/back duplication, one-bar states, and explicit shared-line ownership. "
            "Normal-slot permutations are collapsed because slot order does not change build mechanics."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.potion_frontier",
        domain="extreme",
        purpose=(
            "Enumerate the finite canonical potion effect-family selection denominator "
            "for generated sustained-DPS search without assuming potion activation."
        ),
        implementation_path="services.extreme_sustained_dps_potion_frontier_service",
        inputs=("PlayerBuild", "PotionAvailabilityRepository"),
        outputs=("ExtremeSustainedDPSPotionFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_potion_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Exact reagent formulas sharing one canonical trait family are mechanically "
            "deduplicated. No-potion remains legal. Activation, cooldown, duration, and "
            "Medicinal Use remain runtime-owned."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.passive_rank_frontier",
        domain="extreme",
        purpose=(
            "Index legal passive-rank states for candidate class lines and explicitly "
            "owned combat skill lines without inventing additional line ownership."
        ),
        implementation_path="services.extreme_sustained_dps_passive_rank_frontier_service",
        inputs=("CharacterProgression", "CandidateClass", "ExtremeSkillUniverse"),
        outputs=("ExtremeSustainedDPSPassiveRankFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_passive_rank_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Enumerates rank 0 through canonical max rank lazily. Native class lines are "
            "allowed automatically; shared line ownership must already be explicit. "
            "Racial passive progression remains race-owned."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_effect_projection",
        domain="extreme",
        purpose=(
            "Convert already-active reviewed runtime EffectVariant stat identities into "
            "canonical Effect rows for exact rotation build-context reconstruction."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_effect_projection_service",
        inputs=("ActiveEffectVariants",),
        outputs=("ExtremeSustainedDPSRuntimeEffectProjection",),
        dependencies=("extreme.sustained_dps.gear_runtime_semantics",),
        responsibilities=("extreme_sustained_dps_runtime_effect_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Owns no trigger, timing, cooldown, bar, or persistence logic. Current reviewed "
            "projection includes timed weapon_spell_damage into Weapon Damage and Spell Damage."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_runtime_evaluation",
        domain="extreme",
        purpose=(
            "Evaluate one explicit generated DD build, dual-bar gear state, RotationPlan, "
            "runtime history, and target through canonical Combat Simulation."
        ),
        implementation_path="services.extreme_sustained_dps_generated_runtime_evaluation_service",
        inputs=(
            "PlayerBuild",
            "CharacterProgression",
            "ExtremeDualBarGearState",
            "RotationPlan",
            "ExtremeRuntimeSnapshot",
            "ExplicitTargetAssumptions",
        ),
        outputs=("ExtremeGeneratedSustainedDPSRuntimeResult",),
        dependencies=("extreme.sustained_dps.gear_runtime_semantics", "simulation.saved_build_dd"),
        responsibilities=("extreme_sustained_dps_generated_runtime_evaluation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Generated progression is caller-owned rather than resolved through saved-build persistence. "
            "Bar-legal named gear buffs flow through the shared runtime CombatState path, while reviewed "
            "timed stat EffectVariants are projected into canonical runtime build-context inputs. "
            "Unknown runtime stat identities still fail closed."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.gear_runtime_semantics",
        domain="extreme",
        purpose=(
            "Classify active generated-gear bonus rows as reviewed static, conditional-static, "
            "verified runtime, mixed, or unsupported before sustained-DPS runtime scoring."
        ),
        implementation_path="services.extreme_sustained_dps_gear_runtime_semantic_inventory_service",
        inputs=("ExtremeDualBarGearState", "GearSetRepository"),
        outputs=("ExtremeSustainedDPSGearRuntimeSemanticInventory",),
        dependencies=("extreme.sustained_dps.dual_bar_gear_frontier",),
        responsibilities=("extreme_sustained_dps_gear_runtime_semantics",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Static resolution reuses GearSetEffectResolver; verified runtime identities reuse "
            "the canonical known-effect registry. Runtime identity does not prove proc occurrence, uptime, or DPS."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.dual_bar_gear_frontier",
        domain="extreme",
        purpose=(
            "Compose exhaustively realized sustained-DPS gear-topology branches into "
            "canonical complete front/back equipment states."
        ),
        implementation_path="services.extreme_sustained_dps_dual_bar_gear_frontier_service",
        inputs=("GearTopologyRealizationBranches", "ExpectedTopologyCount"),
        outputs=("ExtremeSustainedDPSDualBarGearFrontier",),
        dependencies=("extreme.sustained_dps.gear_topology_realization",),
        responsibilities=("extreme_sustained_dps_dual_bar_gear_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Denominator proof requires complete topology-branch coverage. Front/back states "
            "must agree on shared body/jewelry equipment and obey canonical bar-access rules."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.gear_topology_frontier",
        domain="extreme",
        purpose=(
            "Expose the canonical active-snapshot gear-set count-partition denominator "
            "as a deterministic pageable sustained-DPS search frontier."
        ),
        implementation_path="services.extreme_sustained_dps_gear_topology_frontier_service",
        inputs=("GearSetRepository",),
        outputs=("ExtremeSustainedDPSGearTopologyFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_gear_topology_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Closes only the abstract active-snapshot count topology. Named-set identity, "
            "physical slot realization, dual-bar coexistence, and runtime set semantics remain separate proofs."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.gear_topology_realization",
        domain="extreme",
        purpose=(
            "Expand one sustained-DPS gear count-topology branch into exact named-set "
            "physical slot witnesses using canonical breakpoints and slot eligibility."
        ),
        implementation_path="services.extreme_sustained_dps_gear_topology_realization_service",
        inputs=("GearTopologyIndex", "OptionalAssignmentCap"),
        outputs=("ExtremeSustainedDPSGearTopologyRealization",),
        dependencies=("extreme.sustained_dps.gear_topology_frontier",),
        responsibilities=("extreme_sustained_dps_gear_topology_realization",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Truncation is explicitly exploratory and withholds denominator proof. "
            "An exhaustive branch with zero legal physical witnesses is a proven-empty branch."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.champion_point_frontier",
        domain="extreme",
        purpose=(
            "Count and page every structurally legal canonical slottable Champion Point "
            "loadout under the four-slots-per-discipline rule without materializing the product."
        ),
        implementation_path="services.extreme_sustained_dps_champion_point_frontier_service",
        inputs=("PlayerBuild", "ChampionPointStaticRepository"),
        outputs=("ExtremeSustainedDPSChampionPointFrontier",),
        dependencies=("mechanics.champion_point_loadout",),
        responsibilities=("extreme_sustained_dps_champion_point_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Preserves all canonical slottable stars and structural Champion Bar legality. "
            "Dynamic/runtime star effects remain unresolved until exact candidate evaluation."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.jewelry_frontier",
        domain="extreme",
        purpose=(
            "Count and page the complete modeled jewelry trait × canonical glyph-family "
            "product for the jewelry slots actually equipped by one build witness."
        ),
        implementation_path="services.extreme_sustained_dps_jewelry_frontier_service",
        inputs=("PlayerBuild", "CanonicalJewelryTraits", "CanonicalJewelryGlyphFamilies"),
        outputs=("ExtremeSustainedDPSJewelryFrontier",),
        dependencies=("extreme.sustained_dps.dynamic_axes",),
        responsibilities=("extreme_sustained_dps_jewelry_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Preserves the joint finite denominator lazily and makes no independent-stat "
            "DPS reduction assumption."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.weapon_frontier",
        domain="extreme",
        purpose=(
            "Count and page the modeled weapon trait × canonical enchant-family product "
            "while preserving weapon-enchant proc/cooldown scoring as a runtime responsibility."
        ),
        implementation_path="services.extreme_sustained_dps_weapon_frontier_service",
        inputs=("PlayerBuild", "CanonicalWeaponTraits", "CanonicalWeaponEnchantFamilies"),
        outputs=("ExtremeSustainedDPSWeaponFrontier",),
        dependencies=("extreme.sustained_dps.dynamic_axes",),
        responsibilities=("extreme_sustained_dps_weapon_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Weapon enchant identities are enumerable statically, but damage, buff/debuff, "
            "proc, cooldown, and Infused interactions remain runtime-owned."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.mundus_provisioning_dominance",
        domain="extreme",
        purpose=(
            "Exhaust the canonical joint Mundus × mapped provisioning grid for one exact "
            "action witness and prove an absolute action-damage ceiling for those axes only."
        ),
        implementation_path="services.extreme_sustained_dps_mundus_provisioning_dominance_service",
        inputs=("PlayerBuild", "MundusChoices", "ProvisioningChoices", "ExactActionEvaluator"),
        outputs=("ExtremeSustainedDPSMundusProvisioningDominanceResult",),
        dependencies=("extreme.sustained_dps.dynamic_axes",),
        responsibilities=("extreme_sustained_dps_mundus_provisioning_dominance",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Searches the full joint finite grid rather than summing independent stat maxima. "
            "Any unresolved combination withholds dominance and keeps pruning fail-open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.action_upper_bound",
        domain="extreme",
        purpose=(
            "Promote exact canonical action-damage occurrences into proof-safe optimistic "
            "action ceilings only when every required future mutation axis is explicitly dominated."
        ),
        implementation_path="services.extreme_sustained_dps_action_upper_bound_service",
        inputs=("RotationActionDamageOccurrenceEvidence", "SustainedDPSActionDominanceProof"),
        outputs=("ExtremeSustainedDPSActionUpperBoundResult",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_action_upper_bound_promotion",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Exact action damage is not automatically an upper bound over unsynthesized gear, "
            "CP, passive, skill-bar, or runtime mutations. Missing dominance proof keeps pruning fail-open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.rotation_upper_bound",
        domain="extreme",
        purpose=(
            "Aggregate externally proven per-action optimistic damage ceilings into one "
            "proof-safe sustained-DPS ceiling for an explicit RotationPlan horizon."
        ),
        implementation_path="services.extreme_sustained_dps_rotation_upper_bound_service",
        inputs=("RotationPlan", "SustainedDPSActionUpperBounds"),
        outputs=("ExtremeSustainedDPSRotationUpperBound",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_rotation_upper_bound",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Arithmetic only: this service does not calculate ESO damage. Every damage-bearing "
            "scheduled action must have a proven optimistic ceiling that includes all periodic "
            "and triggered consequences within the plan horizon or the whole-plan ceiling is withheld."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.pruning",
        domain="extreme",
        purpose=(
            "Apply a legal incumbent to externally proven optimistic sustained-DPS upper "
            "bounds and prune only branches that cannot match or exceed it."
        ),
        implementation_path="services.extreme_sustained_dps_pruning_service",
        inputs=("SustainedDPSUpperBoundEvidence", "IncumbentDPS"),
        outputs=("ExtremeSustainedDPSPruningResult",),
        dependencies=("extreme.sustained_dps.generated_frontier",),
        responsibilities=("extreme_sustained_dps_proof_safe_pruning",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This service never computes ESO damage or invents an upper bound. Missing or "
            "unproven bounds force branches open. Equal-to-incumbent ceilings also remain "
            "open because a tie can affect unique-leader and global-proof semantics."
        ),
    ),
    ServiceDescriptor(
        service_id="combat.simulation.snapshot",
        domain="combat",
        purpose=(
            "Project canonical bar, resource, Health, effect-window, and target state "
            "at an exact simulation timeline coordinate."
        ),
        implementation_path="services.combat_simulation_snapshot_service",
        inputs=("CombatSimulationResult", "TimelineCoordinate"),
        outputs=("CombatSimulationSnapshot",),
        dependencies=("combat.simulation.kernel",),
        responsibilities=("combat_simulation_snapshot_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
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

from services.service_catalog_aggregator import ALL_EXTENSION_SERVICE_DESCRIPTORS

SERVICE_DESCRIPTORS = (*SERVICE_DESCRIPTORS, *ALL_EXTENSION_SERVICE_DESCRIPTORS)
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
