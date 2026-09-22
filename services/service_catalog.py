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
        service_id="extreme.sustained_dps.ultimate_added_action_count_proof",
        domain="extreme",
        purpose=(
            "Promote one explicit generated Ultimate policy's exact scheduled selected-bar "
            "Ultimate count into a proof-safe maximum count of additional damage actions."
        ),
        implementation_path="services.extreme_sustained_dps_ultimate_added_action_count_proof_service",
        inputs=("ExtremeSustainedDPSRotationPolicyCandidate",),
        outputs=("ExtremeSustainedDPSUltimateAddedActionCountResult",),
        dependencies=("extreme.sustained_dps.rotation_policy_frontier",),
        responsibilities=("extreme_sustained_dps_ultimate_added_action_count_proof",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Uses the selected generated policy's exact scheduled Ultimate actions and requires final canonical resource legality. "
            "No generation, cost, scheduling, or damage arithmetic is reimplemented. For one exact policy the scheduled count is both exact and a safe added-action ceiling."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.rotation_family_action_count_proof",
        domain="extreme",
        purpose=(
            "Prove the maximum damage-bearing action count for a generated semi-static "
            "rotation seed family without materializing ordinary-skill permutations."
        ),
        implementation_path="services.extreme_sustained_dps_rotation_family_action_count_proof_service",
        inputs=("RotationFamilyFrontier", "ExactDuration", "OptionalAdditionalPolicyActionCountProof"),
        outputs=("ExtremeSustainedDPSRotationFamilyActionCountResult",),
        dependencies=("extreme.sustained_dps.rotation_plan_frontier",),
        responsibilities=("extreme_sustained_dps_rotation_family_action_count_proof",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Reconstructs only the canonical generated step-kind cycle. Skill permutation does "
            "not change the cycle shape. Weave-on is included when taking the seed-family maximum. "
            "Any later policy that can add damage actions must supply its own proven count ceiling."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_family_branch_bound_adapter",
        domain="extreme",
        purpose=(
            "Promote a proven finite-family whole-plan ceiling into branch-and-bound evidence only after exact branch-scope equivalence is proven."
        ),
        implementation_path="services.extreme_sustained_dps_finite_family_branch_bound_adapter_service",
        inputs=("FiniteWholePlanDominanceResult", "FiniteFamilyBranchScopeProof"),
        outputs=("ExtremeSustainedDPSFiniteFamilyBranchBoundAdaptation",),
        dependencies=(
            "extreme.sustained_dps.finite_whole_plan_dominance",
            "extreme.sustained_dps.generated_branch_and_bound",
        ),
        responsibilities=("extreme_sustained_dps_finite_family_branch_bound_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Local finite-family closure may prune only a branch proven to contain exactly that family. "
            "Every omitted-scope item must be explicitly excluded from the branch before the numeric ceiling is promoted."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_family_node_bound",
        domain="extreme",
        purpose=(
            "Bind one proven finite-family branch ceiling to the exact generated frontier node identity before it enters the partial-branch bound envelope."
        ),
        implementation_path="services.extreme_sustained_dps_finite_family_node_bound_service",
        inputs=("GeneratedFrontierNode", "FiniteWholePlanDominanceResult", "FiniteFamilyBranchScopeProof"),
        outputs=("ExtremeSustainedDPSBoundEnvelopeInput",),
        dependencies=(
            "extreme.sustained_dps.finite_family_branch_bound_adapter",
            "extreme.sustained_dps.partial_branch_upper_bound",
        ),
        responsibilities=("extreme_sustained_dps_finite_family_node_bound",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Fails closed when the branch-scope proof names any node other than the generated node receiving the bound. "
            "The bridge never rewrites a proof onto a sibling branch and never strengthens an unsafe local-family result."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.theoretical_maximum_closure",
        domain="extreme",
        purpose=(
            "Distinguish proof of the searched finite generated denominator from proof of the full theoretical MOST Sustained DPS objective."
        ),
        implementation_path="services.extreme_sustained_dps_theoretical_maximum_closure_service",
        inputs=("GeneratedSearchResult", "CanonicalAxisDominanceComposition", "OmittedTheoreticalScope"),
        outputs=("ExtremeSustainedDPSTheoreticalMaximumClosure",),
        dependencies=(
            "extreme.sustained_dps.axis_dominance_composition",
            "extreme.sustained_dps.generated_branch_and_bound",
        ),
        responsibilities=("extreme_sustained_dps_theoretical_maximum_closure",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "A finite-tree maximum is not promoted to theoretical Objective #32 closure unless every canonical mutation axis is required and covered, "
            "the finite search itself is proven, and no explicit theoretical scope remains omitted."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.structural_axis_coverage",
        domain="extreme",
        purpose=(
            "Promote proven sustained-DPS structural enumeration into canonical race, class-route, and attribute axis coverage without treating inherited active-bar coordinates as Objective #32 coverage."
        ),
        implementation_path="services.extreme_sustained_dps_structural_axis_coverage_service",
        inputs=("ExtremeSustainedDPSGeneratedFrontier",),
        outputs=("ExtremeSustainedDPSStructuralAxisCoverageResult",),
        dependencies=(
            "extreme.sustained_dps.generated_frontier",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_structural_axis_coverage",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Structural enumeration coverage is distinct from generated-tree integration. "
            "The inherited active-bar coordinate is not promoted because sustained-DPS starting-bar semantics are owned by rotation search."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.structural_family_adapter",
        domain="extreme",
        purpose=(
            "Collapse validated front/back structural coordinate pairs into one race/class-route/attribute family for sustained-DPS generated search."
        ),
        implementation_path="services.extreme_sustained_dps_structural_family_adapter_service",
        inputs=("ExtremeSustainedDPSGeneratedCandidateService",),
        outputs=("ExtremeSustainedDPSStructuralFamilyFrontier", "ExtremeSustainedDPSStructuralFamilyChoice"),
        dependencies=(
            "extreme.sustained_dps.generated_frontier",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_structural_family_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Every collapsed family is accepted only when adjacent front/back coordinates have identical race, class route, and attributes and differ only by active_bar. "
            "Starting-bar semantics remain a later rotation-family responsibility."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.structural_materialization",
        domain="extreme",
        purpose=(
            "Materialize one validated sustained-DPS structural family into ordinary PlayerBuild and CharacterProgression state for the existing generated gear pipeline."
        ),
        implementation_path="services.extreme_sustained_dps_structural_materialization_service",
        inputs=("ExtremeSustainedDPSStructuralFamilyChoice",),
        outputs=("ExtremeSustainedDPSStructuralMaterialization",),
        dependencies=("extreme.sustained_dps.structural_family_adapter",),
        responsibilities=("extreme_sustained_dps_structural_materialization",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Copies race, legal class route, and 64-point attributes only. "
            "The structural active-bar duplicate is intentionally not copied into build state because rotation search owns starting-bar behavior."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_axis_inventory",
        domain="extreme",
        purpose=(
            "Inventory which canonical sustained-DPS mutation axes are physically represented by one generated lazy search tree without promoting tree presence into denominator proof."
        ),
        implementation_path="services.extreme_sustained_dps_generated_axis_inventory_service",
        inputs=("IndexedFrontierAxes", "AdditionalCanonicalAxes"),
        outputs=("ExtremeSustainedDPSGeneratedAxisInventory",),
        dependencies=("extreme.sustained_dps.generated_frontier_wiring",),
        responsibilities=("extreme_sustained_dps_generated_axis_inventory",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Axis metadata is structural evidence only. Missing axes remain visible, untagged axes are reported, "
            "and duplicate canonical-axis enumeration is surfaced instead of silently accepted."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.objective32_scenario_preflight",
        domain="extreme",
        purpose=(
            "Validate proof-critical Objective #32 search-time scenario evidence before theoretical-closure traversal begins."
        ),
        implementation_path="services.extreme_sustained_dps_objective32_scenario_preflight_service",
        inputs=(
            "RuntimeStateFrontier",
            "HeavyAttackChannelBlockDenominatorProof",
            "EncounterPolicyAdapter",
        ),
        outputs=("ExtremeSustainedDPSObjective32ScenarioPreflight",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_objective32_scenario_preflight",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Requires an explicit runtime-state frontier with complete denominator proof and no unresolved or omitted scope, plus a proven-complete Heavy Attack encounter channel-block denominator. "
            "The canonical Objective #32 composition enables this guard; generic finite-denominator search wrappers may leave it disabled. "
            "Preflight prevents an obviously non-closure-ready scenario from entering branch-and-bound but cannot prove search completion or exact simulation completeness."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.objective32_composition",
        domain="extreme",
        purpose=(
            "Assemble the canonical generated Objective #32 production service graph from already-configured structural, build, rotation, runtime, and finalized-potion authorities."
        ),
        implementation_path="services.extreme_sustained_dps_objective32_composition_service",
        inputs=(
            "StructuralFamilyFrontier",
            "StructuralMaterializer",
            "GeneratedGearAxisAdapter",
            "GeneratedMundusFoodAxisAdapter",
            "GeneratedLateAxisAdapter",
            "GeneratedEncounterPolicyAxisAdapter",
            "GeneratedRotationAxisAdapter",
            "GeneratedRuntimePolicyAxisAdapter",
            "GeneratedRuntimeEvaluation",
            "FinalizedPotionTimingEvidenceResolver",
            "CandidateRuntimeStateFrontierResolver",
        ),
        outputs=("ExtremeSustainedDPSObjective32Composition",),
        dependencies=(
            "extreme.sustained_dps.generated_axis_pipeline",
            "extreme.sustained_dps.generated_axis_pipeline_leaf_evaluation",
            "extreme.sustained_dps.global_generated_search",
            "extreme.sustained_dps.global_objective32_search",
            "extreme.sustained_dps.generated_finalized_potion_axis_adapter",
            "extreme.sustained_dps.candidate_runtime_state_frontier_resolver",
        ),
        responsibilities=("extreme_sustained_dps_objective32_composition",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This is the canonical production composition root for the generated Objective #32 graph. "
            "It refuses construction unless the canonical Mundus/food and encounter-policy axes are present, finalized potion timing is wired after runtime policy, candidate-resolved runtime_state is wired after the finalized witness, the additional resource-event denominator is explicitly proven complete, and the runtime-policy adapter is configured for complete scheduler-derived Heavy Attack discovery. "
            "Low-level frontier repositories and mechanics remain owned by their existing services rather than being recreated here."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.global_generated_search",
        domain="extreme",
        purpose=(
            "Prepend the validated structural family denominator to the existing generated sustained-DPS axis pipeline and run the resulting global lazy branch-and-bound tree."
        ),
        implementation_path="services.extreme_sustained_dps_global_generated_search_service",
        inputs=(
            "StructuralFamilyFrontier",
            "StructuralMaterializer",
            "GeneratedAxisPipeline",
            "DualBarGearFrontier",
            "ExplicitTargetScenario",
        ),
        outputs=("ExtremeSustainedDPSGeneratedSearchResult",),
        dependencies=(
            "extreme.sustained_dps.structural_family_adapter",
            "extreme.sustained_dps.structural_materialization",
            "extreme.sustained_dps.generated_axis_pipeline",
            "extreme.sustained_dps.generated_frontier_wiring",
            "extreme.sustained_dps.generated_axis_inventory",
            "extreme.sustained_dps.generated_runtime_state_axis_adapter",
        ),
        responsibilities=("extreme_sustained_dps_global_generated_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The first generated axis is race/class-route/attributes. Each selected family is materialized into the ordinary pipeline root before gear and later axes expand. "
            "Unproven structural pairing fails closed. Legacy callers may append one static runtime-state frontier globally; canonical Objective #32 composition instead carries candidate-resolved runtime_state inside the pipeline."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_tree_coverage",
        domain="extreme",
        purpose=(
            "Promote canonical mutation-axis coverage directly from one completed generated search tree and its exact axis inventory while preserving every axis-carried theoretical omission."
        ),
        implementation_path="services.extreme_sustained_dps_generated_tree_coverage_service",
        inputs=("ExtremeSustainedDPSGeneratedSearchResult", "ExtremeSustainedDPSGeneratedAxisInventory"),
        outputs=("ExtremeSustainedDPSGeneratedTreeCoverageResult",),
        dependencies=(
            "extreme.sustained_dps.generated_axis_inventory",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_generated_tree_coverage",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Coverage is withheld unless the finite generated denominator maximum is proven and the inventory itself is unambiguous. "
            "Only physically searched canonical axes are promoted, and local/anchored-family omissions remain attached to the proof."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.objective32_blockers",
        domain="extreme",
        purpose=(
            "Project structured, stable closure blockers for Objective #32 from finite-search state, physical tree axes, canonical coverage, and explicit theoretical omissions."
        ),
        implementation_path="services.extreme_sustained_dps_objective32_blocker_service",
        inputs=(
            "ExtremeSustainedDPSGeneratedSearchResult",
            "ExtremeSustainedDPSGeneratedAxisInventory",
            "ExtremeSustainedDPSAxisDominanceComposition",
            "ExtremeSustainedDPSTheoreticalMaximumClosure",
        ),
        outputs=("ExtremeSustainedDPSObjective32BlockerReport",),
        dependencies=(
            "extreme.sustained_dps.generated_axis_inventory",
            "extreme.sustained_dps.axis_dominance_composition",
            "extreme.sustained_dps.theoretical_maximum_closure",
        ),
        responsibilities=("extreme_sustained_dps_objective32_blocker_reporting",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Stable blocker codes distinguish finite-search debt, physically missing or duplicate axes, coverage debt, unresolved evidence, and explicit theoretical omissions. "
            "Reporting is diagnostic only and cannot create or remove proof."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.global_objective32_search",
        domain="extreme",
        purpose=(
            "Run the structural global generated sustained-DPS tree and produce the end-to-end Objective #32 proof result over that same denominator."
        ),
        implementation_path="services.extreme_sustained_dps_global_objective32_search_service",
        inputs=(
            "GlobalGeneratedSearch",
            "GeneratedAxisInventory",
            "OptionalSupplementalAxisCoverageProofs",
            "OptionalSupplementalCoverageScopeProof",
            "OptionalProvenLocalRuntimeStateFrontier",
        ),
        outputs=(
            "ExtremeSustainedDPSGlobalObjective32SearchResult",
            "ExtremeSustainedDPSObjective32BlockerReport",
        ),
        dependencies=(
            "extreme.sustained_dps.global_generated_search",
            "extreme.sustained_dps.generated_axis_inventory",
            "extreme.sustained_dps.generated_tree_coverage",
            "extreme.sustained_dps.axis_dominance_composition",
            "extreme.sustained_dps.theoretical_maximum_closure",
            "extreme.sustained_dps.objective32_blockers",
            "extreme.sustained_dps.objective32_scenario_preflight",
        ),
        responsibilities=("extreme_sustained_dps_global_objective32_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Canonical axis coverage is derived from the exact completed generated tree rather than caller claims, so no scope certificate is required for same-tree closure. "
            "Supplemental proofs are accepted only when an explicit scope proof ties them to the same denominator; otherwise they are ignored and reported. "
            "The generated-axis inventory must show every canonical axis physically present, and axis-carried omitted scope must be empty, before theoretical closure."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.objective32_search",
        domain="extreme",
        purpose=(
            "Run generated sustained-DPS search and produce one end-to-end Objective #32 result that keeps finite-denominator proof separate from theoretical maximum closure."
        ),
        implementation_path="services.extreme_sustained_dps_objective32_search_service",
        inputs=(
            "GeneratedAxisPipelineRoot",
            "CanonicalAxisCoverageProofs",
            "Objective32SearchScopeProof",
            "OptionalProvenLocalRuntimeStateFrontier",
            "ExplicitTargetScenario",
        ),
        outputs=("ExtremeSustainedDPSObjective32SearchResult",),
        dependencies=(
            "extreme.sustained_dps.generated_axis_pipeline_search",
            "extreme.sustained_dps.generated_runtime_state_axis_adapter",
            "extreme.sustained_dps.axis_dominance_composition",
            "extreme.sustained_dps.theoretical_maximum_closure",
        ),
        responsibilities=("extreme_sustained_dps_objective32_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The wrapper does not invent coverage. Callers supply proof objects for searched axes and an explicit scope proof that those proofs describe the same generated search denominator; "
            "a supplied local runtime frontier contributes only its proven runtime_state coverage. The result reports finite-tree completion and theoretical Objective #32 closure as distinct facts."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.candidate_runtime_state_frontier_resolver",
        domain="extreme",
        purpose=(
            "Resolve the canonical runtime_state frontier separately for each finalized generated Objective #32 candidate."
        ),
        implementation_path="services.extreme_sustained_dps_candidate_runtime_state_frontier_resolver_service",
        inputs=(
            "CompleteFinalizedGeneratedPipelineState",
            "RuntimeScenarioFrontierService",
            "OptionalCandidateDamageOccurrenceProvider",
            "SupplementalScenarioRuntimeEvidenceResolvers",
        ),
        outputs=("ExtremeSustainedDPSCandidateRuntimeStateResolution",),
        dependencies=(
            "extreme.sustained_dps.runtime_scenario_frontier",
        ),
        responsibilities=("extreme_sustained_dps_candidate_runtime_state_frontier_resolver",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Uses the finalized-potion candidate when present, plus the final assembled build and target identity. "
            "The resolver is candidate-scoped so different gear/skills/rotations may produce different runtime effect/event denominators. "
            "Exact damage-occurrence evidence remains injectable to avoid circularly deriving runtime_state from a damage evaluator that itself consumes runtime_state."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_runtime_state_axis_adapter",
        domain="extreme",
        purpose=(
            "Expose runtime_state as either a legacy static terminal frontier or a candidate-resolved terminal axis over each finalized generated witness."
        ),
        implementation_path="services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service",
        inputs=(
            "CompleteGeneratedPipelineState",
            "ProvenLocalRuntimeStateFrontierOrCandidateResolver",
        ),
        outputs=("IndexedFrontierAxis", "RuntimeStateAxisCoverageProof"),
        dependencies=(
            "extreme.sustained_dps.runtime_state_frontier",
            "extreme.sustained_dps.generated_frontier_wiring",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_generated_runtime_state_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Legacy static-frontier mode preserves caller omitted scope. Candidate-resolved mode recomputes the runtime family from each finalized pipeline witness and rejects any unresolved or omitted-scope frontier before exposing runtime_state with no theoretical omission. "
            "Each selected runtime snapshot becomes exact leaf input."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_effect_universe",
        domain="extreme",
        purpose=(
            "Resolve the candidate-scoped runtime-triggered EffectVariant universe from canonical saved-build capability evidence."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_effect_universe_service",
        inputs=("PlayerBuild", "SavedBuildCapabilityService"),
        outputs=("ExtremeSustainedDPSRuntimeEffectUniverse",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_runtime_effect_universe",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Reuses SavedBuildCapabilityService for canonical skill/gear effect discovery and admits only variants with explicit runtime triggers. "
            "potion_use variants are excluded because finalized plan potion state is modeled separately. "
            "Triggerless static/passive variants remain with static/conditional build mechanics, while deferred runtime-effect conversion boundaries fail the runtime universe closed."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_event_skeleton",
        domain="extreme",
        purpose=(
            "Derive the runtime-event skeleton subset already proven by a finalized DD plan and exact-time damage occurrence evidence while leaving encounter-specific trigger families explicit."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_event_skeleton_service",
        inputs=(
            "GeneratedRotationCandidate",
            "CanonicalRuntimeEffectVariants",
            "OptionalDamageOccurrenceProvider",
            "SupplementalScenarioRuntimeEvents",
            "SupplementalEventDenominatorProof",
        ),
        outputs=("ExtremeSustainedDPSRuntimeEventSkeletonResult",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_runtime_event_skeleton",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Scheduled skills, Ultimates, Light Attacks, verified Heavy Attack completions, and exact damage occurrences may own specific trigger skeletons. "
            "Potion-use triggers are excluded because finalized plan POTION actions own potion runtime state. "
            "Expected-value damage/crit math never manufactures critical-hit trigger events; unsupported encounter triggers such as synergies, corpse consumption, off-balance target hits, or heals remain caller-proven scenario event families."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_attempt_evidence_frontier",
        domain="extreme",
        purpose=(
            "Reduce caller-proven runtime event skeletons to a finite complete family of materially distinct chance-roll and condition-context realizations."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service",
        inputs=(
            "RuntimeEventSkeletons",
            "CanonicalEffectVariants",
            "EventSkeletonDenominatorProof",
        ),
        outputs=("ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_runtime_attempt_evidence_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Continuous numeric chance rolls collapse exactly at canonical proc-chance thresholds; one representative is retained for each eligibility-equivalent region. "
            "Condition evidence is enumerated as explicit subsets of relevant named EffectVariant conditions. Event time, trigger, source, target, and sequence remain scenario-owned facts and require their own complete denominator proof."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_external_history_assembly",
        domain="extreme",
        purpose=(
            "Cross finite runtime attempt-evidence choices with a caller-proven finite supplemental condition/group-buff history family."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_external_history_assembly_service",
        inputs=(
            "RuntimeAttemptEvidenceFrontier",
            "SupplementalExternalRuntimeHistories",
            "SupplementalHistoryDenominatorProof",
        ),
        outputs=("ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult",),
        dependencies=(
            "extreme.sustained_dps.runtime_attempt_evidence_frontier",
        ),
        responsibilities=("extreme_sustained_dps_runtime_external_history_assembly",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "An explicitly proven no-supplemental-history scenario becomes one empty supplemental choice rather than an empty denominator. "
            "Any open attempt or supplemental denominator keeps the combined external-history family open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_scenario_frontier",
        domain="extreme",
        purpose=(
            "Build the canonical Objective #32 runtime_state frontier from proven event skeletons, finite chance/condition evidence, supplemental external histories, and plan-owned runtime witness composition."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_scenario_frontier_service",
        inputs=(
            "FinalizedRotationPlan",
            "PlayerBuild",
            "RuntimeEventSkeletons",
            "CanonicalEffectVariants",
            "EventSkeletonDenominatorProof",
            "SupplementalRuntimeHistoryDenominatorProof",
        ),
        outputs=("ExtremeSustainedDPSRuntimeScenarioFrontierResult",),
        dependencies=(
            "extreme.sustained_dps.runtime_effect_universe",
            "extreme.sustained_dps.runtime_event_skeleton",
            "extreme.sustained_dps.runtime_attempt_evidence_frontier",
            "extreme.sustained_dps.runtime_external_history_assembly",
            "extreme.sustained_dps.runtime_external_history_frontier",
        ),
        responsibilities=("extreme_sustained_dps_runtime_scenario_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This is the scenario-facing runtime_state builder. Its candidate-facing path first derives plan/damage-owned event skeletons and leaves only unsupported encounter trigger families to caller proof; the engine then enumerates finite chance/condition realizations, composes plan-owned bar truth, and emits ordinary canonical runtime_state choices. "
            "Explicit omitted scope is preserved so local runtime closure cannot be mistaken for global closure."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_witness_composition",
        domain="extreme",
        purpose=(
            "Compose one controlled Objective #32 ExtremeRuntimeSnapshot from caller-owned external runtime evidence plus RotationPlan-owned bar truth."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_witness_composition_service",
        inputs=(
            "FinalizedRotationPlan",
            "PlayerBuild",
            "ExternalRuntimeHistoryEntries",
        ),
        outputs=("ExtremeSustainedDPSRuntimeWitnessComposition",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_runtime_witness_composition",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Callers may supply proc/event attempts, condition windows, and external group-buff applications. "
            "BAR_SWAP truth is projected from RotationPlan and potion timing is excluded because finalized plan POTION actions own that state downstream. "
            "A proven-empty external history is valid and is distinguished from missing runtime evidence by runtime_history_complete."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_external_history_frontier",
        domain="extreme",
        purpose=(
            "Convert a caller-proven finite family of external runtime histories into the canonical runtime_state frontier for one finalized Objective #32 plan."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_external_history_frontier_service",
        inputs=(
            "FinalizedRotationPlan",
            "PlayerBuild",
            "FiniteExternalRuntimeHistoryFamily",
            "ExternalHistoryDenominatorProof",
        ),
        outputs=("ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult",),
        dependencies=(
            "extreme.sustained_dps.runtime_witness_composition",
            "extreme.sustained_dps.runtime_state_frontier",
        ),
        responsibilities=("extreme_sustained_dps_runtime_external_history_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The caller proves only the genuinely external event-history family. Plan-owned bar transitions and finalized potion timing are removed from caller mutation scope before ordinary runtime_state search begins. "
            "Any invalid history witness or unproven external-history denominator keeps the whole runtime_state denominator open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_state_frontier",
        domain="extreme",
        purpose=(
            "Validate one caller-supplied finite runtime-state family whose local denominator is explicitly proven closed."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_state_frontier_service",
        inputs=("RuntimeStateChoices", "ExternalDenominatorProof", "OmittedScope"),
        outputs=("ExtremeSustainedDPSRuntimeStateFrontier",),
        responsibilities=("extreme_sustained_dps_runtime_state_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Does not infer the universe of proc, cooldown, condition, or encounter timelines. "
            "A finite family closes runtime_state only for the explicitly proven local branch; omitted scope remains visible."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_state_whole_plan_evaluator",
        domain="extreme",
        purpose=(
            "Score explicit runtime-state choices while holding build, progression, gear, plan, target, and horizon fixed."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_state_whole_plan_evaluator_service",
        inputs=("RuntimeStateChoice", "FixedRuntimeStateEvaluationScenario"),
        outputs=("ExtremeSustainedDPSWholePlanEvaluation",),
        dependencies=("extreme.sustained_dps.generated_runtime_evaluation",),
        responsibilities=("extreme_sustained_dps_runtime_state_whole_plan_evaluator",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Only ExtremeRuntimeSnapshot varies. Combat mechanics remain owned by generated runtime evaluation."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.runtime_state_dominance_search",
        domain="extreme",
        purpose=(
            "Compose a proven finite runtime-state family with canonical whole-plan evaluation into a runtime_state pruning ceiling."
        ),
        implementation_path="services.extreme_sustained_dps_runtime_state_dominance_search_service",
        inputs=("ExtremeSustainedDPSRuntimeStateFrontier", "FixedRuntimeStateEvaluationScenario"),
        outputs=("ExtremeSustainedDPSFiniteWholePlanDominanceResult",),
        dependencies=(
            "extreme.sustained_dps.runtime_state_whole_plan_evaluator",
            "extreme.sustained_dps.finite_whole_plan_dominance",
        ),
        responsibilities=("extreme_sustained_dps_runtime_state_dominance_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Promotes runtime_state only when the supplied local denominator and every modeled runtime choice close "
            "over one shared horizon. Omitted runtime scope remains separate from the local ceiling."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.dynamic_whole_plan_frontier_adapter",
        domain="extreme",
        purpose=(
            "Expose generated seed-rotation, anchored Ultimate/potion, execute, and Heavy Attack policy families "
            "through the indexed finite whole-plan dominance contract without eager materialization."
        ),
        implementation_path="services.extreme_sustained_dps_dynamic_whole_plan_frontier_adapter_service",
        inputs=("GeneratedDynamicFrontier",),
        outputs=("ExtremeSustainedDPSIndexedWholePlanAdapter",),
        dependencies=(
            "extreme.sustained_dps.rotation_plan_frontier",
            "extreme.sustained_dps.rotation_policy_frontier",
            "extreme.sustained_dps.execute_policy_frontier",
            "extreme.sustained_dps.heavy_attack_policy_frontier",
            "extreme.sustained_dps.finite_whole_plan_dominance",
        ),
        responsibilities=("extreme_sustained_dps_dynamic_whole_plan_frontier_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Adapters preserve each source denominator and omitted scope. Seed rotation maps to rotation_order + "
            "light_attack_weave; anchored Ultimate/potion maps to ultimate_policy + potion_timing_policy; execute and "
            "Heavy Attack remain separate policy axes. Choices are materialized one at a time."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_whole_plan_choice_evaluator",
        domain="extreme",
        purpose=(
            "Evaluate generated dynamic plan choices against one fixed build/progression/gear/runtime/target witness "
            "through the canonical generated sustained-DPS Combat Simulation path."
        ),
        implementation_path="services.extreme_sustained_dps_generated_whole_plan_choice_evaluator_service",
        inputs=("WholePlanRuntimeScenario", "DynamicPlanChoice"),
        outputs=("ExtremeSustainedDPSWholePlanEvaluation",),
        dependencies=("extreme.sustained_dps.generated_runtime_evaluation",),
        responsibilities=("extreme_sustained_dps_generated_whole_plan_choice_evaluator",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Holds build, explicit progression, dual-bar gear, authoritative runtime history, and target assumptions fixed. "
            "Only the legal plan choice and its initial bar vary. Combat mechanics remain owned by generated runtime evaluation."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_whole_plan_dominance",
        domain="extreme",
        purpose=(
            "Exhaust one proven finite dynamic family through complete same-horizon modeled sustained-DPS "
            "evaluation and promote the largest exact whole-plan score as the family pruning ceiling."
        ),
        implementation_path="services.extreme_sustained_dps_finite_whole_plan_dominance_service",
        inputs=("FiniteDynamicFrontier", "WholePlanEvaluator", "RequiredDuration"),
        outputs=("ExtremeSustainedDPSFiniteWholePlanDominanceResult",),
        dependencies=(
            "extreme.sustained_dps.axis_dominance_composition",
            "extreme.sustained_dps.pruning",
        ),
        responsibilities=("extreme_sustained_dps_finite_whole_plan_dominance",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Plan shape and action identity may differ across choices. Every choice must instead resolve complete "
            "modeled DPS over one exact horizon. Omitted scope remains separate from finite-family closure."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.combat_dynamic_axis_coverage",
        domain="extreme",
        purpose=(
            "Promote proven finite skill-bar, seed-rotation, anchored Ultimate/potion, execute, "
            "and reviewed Heavy Attack policy denominators into canonical dynamic-axis coverage."
        ),
        implementation_path="services.extreme_sustained_dps_combat_dynamic_axis_coverage_service",
        inputs=("GeneratedCombatDynamicFrontier",),
        outputs=("ExtremeSustainedDPSCombatDynamicAxisCoverageResult",),
        dependencies=("extreme.sustained_dps.axis_dominance_composition",),
        responsibilities=("extreme_sustained_dps_combat_dynamic_axis_coverage",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Promotes only finite denominator closure actually proven by each frontier. Anchored potion timing "
            "does not close continuous first-use offsets; Ultimate affordability choice does not close arbitrary "
            "post-affordability delay; Heavy Attack coverage is limited to caller-reviewed safe windows."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_family_dominance_search",
        domain="extreme",
        purpose=(
            "Compose lazy frontier adapters, canonical exact-action evaluators, and the generic finite-axis "
            "dominance engine into reusable Champion Point, passive-rank, and dual-bar gear searches."
        ),
        implementation_path="services.extreme_sustained_dps_finite_family_dominance_search_service",
        inputs=("BaselineBuild", "BaselineProgression", "ExactActionScenario", "FiniteFamilyFrontier"),
        outputs=("ExtremeSustainedDPSFiniteAxisActionDominanceResult",),
        dependencies=(
            "extreme.sustained_dps.finite_axis_frontier_adapter",
            "extreme.sustained_dps.finite_axis_canonical_action_evaluator",
            "extreme.sustained_dps.finite_axis_action_dominance",
        ),
        responsibilities=("extreme_sustained_dps_finite_family_dominance_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Composition only. CP, passive ranks, and dual-bar named gear retain their own frontier authorities; "
            "damage remains owned by the canonical DD provider stack and proof arithmetic by finite-axis dominance."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_axis_canonical_action_evaluator",
        domain="extreme",
        purpose=(
            "Evaluate one fixed scheduled action for generated CP, passive-rank, or dual-bar gear choices "
            "through the canonical Combat Simulation DD provider stack."
        ),
        implementation_path="services.extreme_sustained_dps_finite_axis_canonical_action_evaluator_service",
        inputs=("BaselineBuild", "BaselineProgression", "ExactActionScenario", "FiniteAxisChoice"),
        outputs=("RotationActionDamageOccurrenceEvidence",),
        dependencies=(
            "simulation.saved_build_dd",
            "extreme.sustained_dps.finite_axis_frontier_adapter",
        ),
        responsibilities=("extreme_sustained_dps_finite_axis_canonical_action_evaluator",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Owns adaptation only, not ESO damage math. CP swaps the build CP loadout, passive search swaps "
            "explicit progression ranks, and gear materializes one legal dual-bar state before delegating to "
            "CombatSimulationSavedBuildDDProviderService. Unresolved runtime mechanics remain fail-closed."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_axis_frontier_adapter",
        domain="extreme",
        purpose=(
            "Expose complete generated Champion Point, passive-rank, and dual-bar named-gear "
            "frontiers through the indexed finite-axis dominance contract without eager materialization."
        ),
        implementation_path="services.extreme_sustained_dps_finite_axis_frontier_adapter_service",
        inputs=("GeneratedFiniteFrontier", "BaselineBuildOrProgression"),
        outputs=("ExtremeSustainedDPSIndexedChoiceAdapter",),
        dependencies=(
            "extreme.sustained_dps.champion_point_frontier",
            "extreme.sustained_dps.passive_rank_frontier",
            "extreme.sustained_dps.dual_bar_gear_frontier",
            "extreme.sustained_dps.finite_axis_action_dominance",
        ),
        responsibilities=("extreme_sustained_dps_finite_axis_frontier_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Adapters expose choice_count + choice_at(index) and preserve the source frontier's "
            "denominator proof. CP maps to champion_points, passive ranks to passive_ranks, and "
            "dual-bar named gear to gear_topology + named_gear_realization. Choices are materialized one at a time."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finite_axis_action_dominance",
        domain="extreme",
        purpose=(
            "Exhaust one caller-supplied proven finite mutation-axis denominator for one "
            "exact scheduled damage action and promote both canonical axis coverage and "
            "the largest exact action consequence."
        ),
        implementation_path="services.extreme_sustained_dps_finite_axis_action_dominance_service",
        inputs=("CandidateKey", "CanonicalAxes", "FiniteChoices", "ExactActionEvaluator"),
        outputs=("ExtremeSustainedDPSFiniteAxisActionDominanceResult",),
        dependencies=(
            "extreme.sustained_dps.axis_dominance_composition",
            "extreme.sustained_dps.structural_action_upper_bound",
        ),
        responsibilities=("extreme_sustained_dps_finite_axis_action_dominance",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Every non-target axis remains caller-fixed. Every finite choice must resolve the "
            "same scheduled action coordinate. Incomplete denominators, coordinate drift, or "
            "unresolved action consequences promote neither axis coverage nor numeric ceiling."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.gear_progression_axis_coverage",
        domain="extreme",
        purpose=(
            "Promote proven dual-bar named-gear, Champion Point, and passive-rank "
            "denominator closure into canonical sustained-DPS mutation-axis coverage."
        ),
        implementation_path="services.extreme_sustained_dps_gear_progression_axis_coverage_service",
        inputs=("DualBarGearFrontierOrProgressionFrontier",),
        outputs=("ExtremeSustainedDPSStructuralAxisCoverageResult",),
        dependencies=("extreme.sustained_dps.axis_dominance_composition",),
        responsibilities=("extreme_sustained_dps_gear_progression_axis_coverage",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Promotes only what each structural denominator actually proves: dual-bar gear "
            "covers gear_topology + named_gear_realization, CP covers champion_points, and "
            "passive search covers passive_ranks. Traits, enchants, runtime behavior, racial "
            "progression, and numeric damage dominance remain separate proof obligations."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.mundus_provisioning_proof_adapter",
        domain="extreme",
        purpose=(
            "Translate a complete joint Mundus × provisioning finite-grid dominance result "
            "into canonical mutation-axis coverage and an absolute per-action damage ceiling."
        ),
        implementation_path="services.extreme_sustained_dps_mundus_provisioning_proof_adapter_service",
        inputs=("ExtremeSustainedDPSMundusProvisioningDominanceResult",),
        outputs=("ExtremeSustainedDPSMundusProvisioningProofAdapterResult",),
        dependencies=(
            "extreme.sustained_dps.mundus_provisioning_dominance",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_mundus_provisioning_proof_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Promotes mundus+food only as one coupled proof. Incomplete joint denominators "
            "promote neither canonical axis coverage nor numeric action ceiling."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.axis_dominance_composition",
        domain="extreme",
        purpose=(
            "Compose canonical generated sustained-DPS mutation-axis coverage from "
            "multiple independent dominance proofs without mixing coverage with numeric optimism."
        ),
        implementation_path="services.extreme_sustained_dps_axis_dominance_composition_service",
        inputs=("CandidateKey", "RequiredMutationAxes", "AxisCoverageProofs"),
        outputs=("ExtremeSustainedDPSAxisDominanceComposition",),
        dependencies=("extreme.sustained_dps.action_upper_bound",),
        responsibilities=("extreme_sustained_dps_axis_dominance_composition",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Uses one canonical axis vocabulary, unions proof coverage, rejects unknown axes, "
            "and leaves numeric optimistic multipliers/absolute ceilings to the action-bound authority. "
            "Missing required axes keep the composed dominance proof incomplete."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.closed_descendant_action_ceiling",
        domain="extreme",
        purpose=(
            "Promote complete canonical damage consequences across one proven-closed "
            "descendant denominator into an absolute per-action total-damage ceiling."
        ),
        implementation_path="services.extreme_sustained_dps_closed_descendant_action_ceiling_service",
        inputs=("BranchKey", "ClosedDescendantKeys", "ClosedDescendantActionWitnesses"),
        outputs=("ExtremeSustainedDPSClosedDescendantActionCeilingResult",),
        dependencies=("extreme.sustained_dps.structural_action_upper_bound",),
        responsibilities=("extreme_sustained_dps_closed_descendant_action_ceiling",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Requires every descendant and every damage-bearing action to be represented exactly, "
            "with explicit direct/periodic/triggered completeness. The maximum exact action "
            "consequence is valid only for that proven-closed branch and is never extrapolated outward."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.structural_action_upper_bound",
        domain="extreme",
        purpose=(
            "Convert a proven maximum damage-bearing action count and a proven absolute "
            "per-action total-damage ceiling into a branch sustained-DPS upper bound."
        ),
        implementation_path="services.extreme_sustained_dps_structural_action_upper_bound_service",
        inputs=("CandidateKey", "ExactDuration", "DamageActionCountProof", "AbsoluteActionDamageCeiling"),
        outputs=("ExtremeSustainedDPSStructuralActionCeiling",),
        dependencies=("extreme.sustained_dps.pruning",),
        responsibilities=("extreme_sustained_dps_structural_action_upper_bound",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Arithmetic only. It infers no ESO action rate or damage formula. The action ceiling "
            "must already cover all direct, periodic, and triggered consequences attributable "
            "to one scheduled damage action inside the same horizon."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.partial_branch_upper_bound",
        domain="extreme",
        purpose=(
            "Intersect independent externally proven optimistic sustained-DPS ceilings "
            "for one partial generated branch and inherit any proven parent ceiling."
        ),
        implementation_path="services.extreme_sustained_dps_partial_branch_upper_bound_service",
        inputs=("CandidateKey", "UpperBoundEvidenceSources", "OptionalParentBound"),
        outputs=("ExtremeSustainedDPSBoundEnvelope",),
        dependencies=("extreme.sustained_dps.pruning",),
        responsibilities=("extreme_sustained_dps_partial_branch_upper_bound",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Safe ceilings for the same branch are intersected with min(), never summed, "
            "so overlapping mechanics cannot double-count optimistic contribution. "
            "Missing/unproven local evidence cannot weaken an inherited proven parent ceiling."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_gear_axis_adapter",
        domain="extreme",
        purpose=(
            "Adapt one proven dual-bar gear catalog plus armor, jewelry, and weapon "
            "trait/enchant frontiers into ordered indexed generated-search axes."
        ),
        implementation_path="services.extreme_sustained_dps_generated_gear_axis_adapter_service",
        inputs=("PlayerBuild", "CharacterProgression", "ProvenDualBarGearFrontier"),
        outputs=("IndexedFrontierAxes", "ExtremeSustainedDPSGeneratedGearAxisState"),
        dependencies=(
            "extreme.sustained_dps.dual_bar_gear_frontier",
            "extreme.sustained_dps.armor_trait_enchant_frontier",
            "extreme.sustained_dps.jewelry_frontier",
            "extreme.sustained_dps.weapon_frontier",
            "extreme.sustained_dps.cross_axis_context",
            "extreme.sustained_dps.generated_frontier_wiring",
        ),
        responsibilities=("extreme_sustained_dps_generated_gear_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Dual-bar compatibility must already be denominator-proven. Later trait/enchant "
            "frontiers mutate the same evolving materialized build in order, preserving prior "
            "axis choices. Unresolved denominators fail closed."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_mundus_food_axis_adapter",
        domain="extreme",
        purpose=(
            "Enumerate a proven finite Mundus and food denominator as exact generated-search build mutations rather than using action-level dominance to choose the final witness."
        ),
        implementation_path="services.extreme_sustained_dps_generated_mundus_food_axis_adapter_service",
        inputs=("CrossAxisContext", "ProvenMundusChoices", "ProvenFoodChoices"),
        outputs=("IndexedFrontierAxes", "MundusFoodAxisCoverageProof"),
        dependencies=(
            "extreme.sustained_dps.generated_frontier_wiring",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_generated_mundus_food_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Mundus is selected before food and both choices are written onto the evolving exact build witness. "
            "The adapter requires an explicitly proven finite denominator; action-level joint dominance remains a pruning proof, not a final-build selector."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_axis_pipeline_search",
        domain="extreme",
        purpose=(
            "Run one composed generated-axis root through lazy proof-safe search under "
            "one target scenario and comparison horizon, optionally enumerating a proven local runtime-state family."
        ),
        implementation_path="services.extreme_sustained_dps_generated_axis_pipeline_search_service",
        inputs=(
            "ExtremeSustainedDPSGeneratedAxisPipelineState",
            "AuthoritativeRuntimeSnapshot",
            "OptionalProvenLocalRuntimeStateFrontier",
            "ExplicitTargetScenario",
        ),
        outputs=("ExtremeSustainedDPSGeneratedSearchResult",),
        dependencies=(
            "extreme.sustained_dps.generated_axis_pipeline",
            "extreme.sustained_dps.generated_axis_pipeline_leaf_evaluation",
            "extreme.sustained_dps.generated_frontier_wiring",
            "extreme.sustained_dps.generated_runtime_state_axis_adapter",
            "extreme.sustained_dps.generated_branch_and_bound",
        ),
        responsibilities=(
            "extreme_sustained_dps_generated_axis_pipeline_search",
        ),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "All exact leaves share the caller's duration, target Health, resistance, identity, and initial bar. "
            "Without a local runtime frontier they also share the fallback runtime snapshot; with one, the proven runtime family is a final indexed axis. "
            "Root, node, and axis-local proof-safe bound providers remain optional; missing bounds force refinement rather than guessing."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_axis_pipeline_leaf_evaluation",
        domain="extreme",
        purpose=(
            "Extract complete generated pipeline witnesses and delegate exact leaf "
            "scoring to the canonical generated-runtime Combat Simulation evaluator."
        ),
        implementation_path="services.extreme_sustained_dps_generated_axis_pipeline_leaf_evaluation_service",
        inputs=(
            "ExtremeSustainedDPSGeneratedFrontierNode",
            "AuthoritativeRuntimeSnapshot",
            "ExplicitTargetScenario",
        ),
        outputs=("ExtremeSustainedDPSExactLeafEvaluation",),
        dependencies=(
            "extreme.sustained_dps.generated_axis_pipeline",
            "extreme.sustained_dps.generated_runtime_evaluation",
            "extreme.sustained_dps.generated_search_evidence_adapter",
        ),
        responsibilities=(
            "extreme_sustained_dps_generated_axis_pipeline_leaf_evaluation",
        ),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Uses the final assembled build/progression and the final generated plan, including finalized potion timing when that late axis is configured. "
            "When a generated local runtime-state choice is present, that choice's snapshot overrides the fallback search snapshot and its evidence is retained. "
            "Missing build, progression, physical gear, plan, or incomplete pipeline state becomes incomplete exact-leaf evidence without invoking simulation."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.encounter_policy_frontier",
        domain="extreme",
        purpose=(
            "Validate one explicit finite sustained-DPS encounter-policy family whose choices carry canonical RotationDemandWindow inputs without inventing encounter timing."
        ),
        implementation_path="services.extreme_sustained_dps_encounter_policy_frontier_service",
        inputs=("EncounterPolicyChoices", "ExternalDenominatorProof", "OmittedScope"),
        outputs=("ExtremeSustainedDPSEncounterPolicyFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_encounter_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "The frontier validates caller-supplied canonical demand windows only. Missing review, threshold-to-clock projection, and wider encounter families remain explicit instead of becoming empty policy."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.encounter_policy_registry_bridge",
        domain="extreme",
        purpose=(
            "Bridge one selected encounter's reviewed Rotation encounter-demand registry entry and canonical boss-guide timing evidence into a finite sustained-DPS encounter-policy frontier."
        ),
        implementation_path="services.extreme_sustained_dps_encounter_policy_registry_bridge_service",
        inputs=(
            "EncounterId",
            "RotationEncounterDemandPolicyRegistryEntry",
            "EncounterBossGuide",
            "OptionalThresholdClockProjection",
        ),
        outputs=("ExtremeSustainedDPSEncounterPolicyFrontier",),
        dependencies=(
            "extreme.sustained_dps.encounter_policy_frontier",
            "rotation.encounter_demand_policy.registry",
            "encounter.boss_guide.read_model",
        ),
        responsibilities=("extreme_sustained_dps_encounter_policy_registry_bridge",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Uses EncounterRotationDemandService for reviewed clock-window projection. Explicitly empty reviewed policy becomes a proven no-demand choice; "
            "missing registry entries, review blockers, unresolved clock facts, or threshold policy without a proven threshold-to-clock projection keep encounter_policy open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_encounter_policy_axis_adapter",
        domain="extreme",
        purpose=(
            "Enumerate a proven finite encounter-policy family immediately before generated rotation-plan search and expose canonical encounter_policy axis coverage."
        ),
        implementation_path="services.extreme_sustained_dps_generated_encounter_policy_axis_adapter_service",
        inputs=("AssembledCandidate", "ProvenEncounterPolicyFrontier"),
        outputs=("IndexedFrontierAxis", "EncounterPolicyAxisCoverageProof"),
        dependencies=(
            "extreme.sustained_dps.encounter_policy_frontier",
            "extreme.sustained_dps.generated_frontier_wiring",
            "extreme.sustained_dps.axis_dominance_composition",
        ),
        responsibilities=("extreme_sustained_dps_generated_encounter_policy_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Selected demand windows flow into the canonical rotation duration-refinement path through explicit ability priorities. "
            "The adapter owns policy enumeration only; RotationDurationRefinementService remains scheduling authority."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_axis_pipeline",
        domain="extreme",
        purpose=(
            "Compose gear, late-build, rotation, evidence-gated runtime-policy, and optional finalized-potion "
            "adapter states into one lazy indexed generated-search pipeline."
        ),
        implementation_path="services.extreme_sustained_dps_generated_axis_pipeline_service",
        inputs=(
            "GeneratedGearAxisRootInputs",
            "GeneratedRotationRuntimeEvidence",
        ),
        outputs=(
            "IndexedFrontierAxes",
            "ExtremeSustainedDPSGeneratedAxisPipelineState",
        ),
        dependencies=(
            "extreme.sustained_dps.generated_gear_axis_adapter",
            "extreme.sustained_dps.generated_mundus_food_axis_adapter",
            "extreme.sustained_dps.generated_late_axis_adapter",
            "extreme.sustained_dps.generated_encounter_policy_axis_adapter",
            "extreme.sustained_dps.generated_rotation_axis_adapter",
            "extreme.sustained_dps.generated_runtime_policy_axis_adapter",
            "extreme.sustained_dps.generated_finalized_potion_axis_adapter",
            "extreme.sustained_dps.generated_runtime_state_axis_adapter",
            "extreme.sustained_dps.generated_frontier_wiring",
        ),
        responsibilities=("extreme_sustained_dps_generated_axis_pipeline",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Explicit immutable stage transitions preserve each adapter's native state, optionally insert exact-witness Mundus/food mutation after gear, "
            "optionally insert a finite encounter-policy selection after build assembly and before rotation generation, reset downstream selections after upstream mutation, "
            "optionally append canonical finalized potion timing after runtime policy, optionally append candidate-resolved runtime_state after the finalized witness, forward axis-local bound providers, and derive stable runtime candidate identity from selected structural rotation coordinates."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_runtime_policy_axis_adapter",
        domain="extreme",
        purpose=(
            "Adapt explicit canonical execute variants plus either legacy reviewed Heavy Attack windows or scheduler-derived complete Heavy Attack timing into ordered indexed generated-search axes."
        ),
        implementation_path="services.extreme_sustained_dps_generated_runtime_policy_axis_adapter_service",
        inputs=(
            "ExtremeSustainedDPSRotationPolicyCandidate",
            "ExecuteRuntimeEvidence",
            "ReviewedHeavyAttackWindowsOrEncounterChannelBlockProof",
        ),
        outputs=(
            "IndexedFrontierAxes",
            "ExtremeSustainedDPSGeneratedRuntimePolicyAxisState",
        ),
        dependencies=(
            "extreme.sustained_dps.execute_policy_frontier",
            "extreme.sustained_dps.heavy_attack_policy_frontier",
            "extreme.sustained_dps.heavy_attack_window_discovery",
            "extreme.sustained_dps.generated_frontier_wiring",
        ),
        responsibilities=(
            "extreme_sustained_dps_generated_runtime_policy_axis_adapter",
        ),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Execute policy receives explicit priorities, snapshot resolver, target identity, and duration rules. "
            "Legacy mode recomputes Heavy Attack expansion from caller-reviewed windows and retains omitted scope. "
            "Complete-discovery mode probes every finalized execute-plan skill slot through the canonical scheduler and refuses traversal without a proven encounter channel-block denominator; only that mode exposes heavy_attack_policy with no omitted scope."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.potion_observation_frontier",
        domain="extreme",
        purpose=(
            "Collect the finite exact DD runtime observation coordinates that can distinguish potion timing on one finalized descendant plan."
        ),
        implementation_path="services.extreme_sustained_dps_potion_observation_frontier_service",
        inputs=(
            "FinalizedRotationPlan",
            "ReviewedPeriodicRuntimeProjections",
            "VerifiedHeavyAttackCompletionEvidence",
        ),
        outputs=("ExtremeSustainedDPSPotionObservationFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_potion_observation_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Scheduled skills, Ultimates, and Light Attacks contribute their exact action coordinates; Heavy Attacks contribute verified completion time; reviewed periodic projections contribute every concrete tick. "
            "Missing Heavy Attack completion evidence or unresolved periodic runtime evidence keeps the observation denominator open."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.potion_resource_observation_frontier",
        domain="extreme",
        purpose=(
            "Collect a proof-safe finite resource-timeline timestamp denominator for finalized potion instant-restoration timing."
        ),
        implementation_path="services.extreme_sustained_dps_potion_resource_observation_frontier_service",
        inputs=(
            "FinalizedRotationPlan",
            "VerifiedHeavyAttackCompletionEvidence",
            "CallerProvenAdditionalResourceEventTimes",
        ),
        outputs=("ExtremeSustainedDPSPotionResourceObservationFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_potion_resource_observation_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Retains every scheduled action timestamp, canonical two-second recovery tick, verified Heavy Attack completion, and caller-supplied resource maximum/restoration timestamp. "
            "Extra breakpoints are proof-safe; omitted external resource-event families are not, so caller completeness evidence is mandatory."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.potion_timing_breakpoint_frontier",
        domain="extreme",
        purpose=(
            "Reduce continuous potion first-use offsets to a finite exact family of activation/expiry boundaries and open-interval representatives for one explicit finalized observation set."
        ),
        implementation_path="services.extreme_sustained_dps_potion_timing_breakpoint_frontier_service",
        inputs=(
            "FinalizedObservationTimes",
            "EffectivePotionBuffDurations",
            "PotionCooldownSeconds",
            "ExactDurationSeconds",
        ),
        outputs=("ExtremeSustainedDPSPotionTimingBreakpointFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_potion_timing_breakpoint_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Closes named-buff first-use timing only for the supplied finite observation set. "
            "Exact action-time boundaries still require before/after ordering during materialization, and potion instant-restoration timing remains explicit omitted scope until separately proven."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.candidate_potion_restoration_evidence",
        domain="rotation",
        purpose=(
            "Project exact scheduled POTION actions into canonical Phase 4 resource-restoration events from sourced PotionUseEvent instant-restore evidence."
        ),
        implementation_path="services.rotation_candidate_potion_restoration_evidence_service",
        inputs=("PlayerBuild", "GeneratedRotationCandidate", "PotionUseEventResolver"),
        outputs=("RotationCandidateRestorationEvidence",),
        dependencies=(),
        responsibilities=("rotation_candidate_potion_restoration_evidence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS", "HEALER", "TANK"),
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Emits sourced Magicka, Stamina, and Health restoration rows at the exact scheduled potion timestamps. "
            "Potion identity mismatch, unresolved source data, unsupported restore traits, and non-integral sourced magnitudes fail closed; Phase 4 retains resource filtering, cap/waste, and ordering authority."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finalized_potion_timing_evidence",
        domain="extreme",
        purpose=(
            "Resolve authoritative finalized periodic, Heavy Attack completion, and caller-certified additional resource-event timing evidence for the late potion axis."
        ),
        implementation_path="services.extreme_sustained_dps_finalized_potion_timing_evidence_service",
        inputs=(
            "GeneratedRotationCandidate",
            "ReviewedDDPeriodicRuntimeSemantics",
            "OptionalActivationAnchorResolver",
            "OptionalAdditionalResourceEventTimes",
        ),
        outputs=("ExtremeSustainedDPSFinalizedPotionTimingEvidence",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_finalized_potion_timing_evidence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Reuses RotationDDPeriodicRuntimeSemanticsRegistryService, RotationCandidatePeriodicDamageRuntimeProjectionService, and RotationHeavySustainProjectionService instead of rescheduling mechanics. "
            "Additional resource maximum/restoration events remain caller-owned; asserting their denominator complete is an explicit proof claim."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.finalized_potion_timing_denominator",
        domain="extreme",
        purpose=(
            "Compose a finalized DD observation frontier with canonical PotionUseEvent and Medicinal Use duration evidence into a finite potion named-buff timing denominator."
        ),
        implementation_path="services.extreme_sustained_dps_finalized_potion_timing_denominator_service",
        inputs=(
            "PlayerBuild",
            "CharacterProgression",
            "ExtremeSustainedDPSPotionObservationFrontier",
            "PotionCooldownSeconds",
        ),
        outputs=("ExtremeSustainedDPSFinalizedPotionTimingDenominator",),
        dependencies=(
            "extreme.sustained_dps.potion_observation_frontier",
            "extreme.sustained_dps.potion_resource_observation_frontier",
            "extreme.sustained_dps.potion_timing_breakpoint_frontier",
        ),
        responsibilities=("extreme_sustained_dps_finalized_potion_timing_denominator",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Potion buff durations remain owned by PotionCadence using explicit Medicinal Use rank. "
            "Damage/runtime observation timestamps and caller-proven resource-timeline timestamps are merged into one conservative breakpoint denominator. "
            "Full potion timing closes only when the resource-event observation denominator is also proven complete."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_finalized_potion_axis_adapter",
        domain="extreme",
        purpose=(
            "Enumerate canonical potion_timing_policy only after execute and Heavy Attack descendants are finalized, replacing provisional potion actions with the complete finite breakpoint family."
        ),
        implementation_path="services.extreme_sustained_dps_generated_finalized_potion_axis_adapter_service",
        inputs=(
            "CompleteGeneratedRuntimePolicyState",
            "ExtremeSustainedDPSFinalizedPotionTimingEvidenceResolver",
            "PlayerBuild",
            "CharacterProgression",
        ),
        outputs=(
            "IndexedFrontierAxis",
            "ExtremeSustainedDPSGeneratedFinalizedPotionAxisState",
        ),
        dependencies=(
            "extreme.sustained_dps.finalized_potion_timing_evidence",
            "extreme.sustained_dps.finalized_potion_timing_denominator",
            "extreme.sustained_dps.potion_resource_observation_frontier",
            "extreme.sustained_dps.generated_frontier_wiring",
        ),
        responsibilities=("extreme_sustained_dps_generated_finalized_potion_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The axis includes explicit no-use, exact boundary before/after ordering where DD state can differ, and one representative for each open continuous-time interval. "
            "It fails closed unless periodic/Heavy Attack observations and additional resource-event timing are proven complete; only then does it expose canonical potion_timing_policy coverage with no omitted scope."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.delayed_ultimate_policy_frontier",
        domain="extreme",
        purpose=(
            "Enumerate every legal delayed Ultimate cast sequence over the exact same-bar SKILL slots of one seed RotationPlan using explicit shared Ultimate generation."
        ),
        implementation_path="services.extreme_sustained_dps_delayed_ultimate_policy_frontier_service",
        inputs=(
            "RotationPlan",
            "UltimateSpendRule",
            "ExplicitUltimateGenerationEvents",
            "StartingUltimate",
        ),
        outputs=("ExtremeSustainedDPSDelayedUltimatePolicyFrontier",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_delayed_ultimate_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Enumerates cast/skip branches over exact scheduled same-bar skill slots and deducts each selected cast from the shared Ultimate balance. "
            "Generation at the exact cast timestamp is not borrowed ahead of the cast. The generated Objective #32 rotation axis consumes this family directly and defers only potion timing to the finalized descendant axis."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_rotation_axis_adapter",
        domain="extreme",
        purpose=(
            "Adapt generated seed/cadence rotation plans and delayed-Ultimate policies "
            "into ordered indexed generated-search axes while deferring canonical potion timing to the finalized descendant axis."
        ),
        implementation_path="services.extreme_sustained_dps_generated_rotation_axis_adapter_service",
        inputs=(
            "ExtremeSustainedDPSAssembledCandidate",
            "RotationPolicyRuntimeEvidence",
        ),
        outputs=("IndexedFrontierAxes", "ExtremeSustainedDPSGeneratedRotationAxisState"),
        dependencies=(
            "extreme.sustained_dps.rotation_plan_frontier",
            "extreme.sustained_dps.rotation_policy_frontier",
            "extreme.sustained_dps.generated_frontier_wiring",
        ),
        responsibilities=("extreme_sustained_dps_generated_rotation_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The adapter preserves plan-before-policy dependency and fails closed on either unproven denominator. "
            "Generated Objective #32 traversal selects only the combined frontier's explicit potion:none slice, so this axis owns delayed Ultimate timing only. "
            "Selected encounter demand windows and ability priorities flow into canonical rotation-plan refinement; finalized potion timing is enumerated later after execute and Heavy Attack policy selection."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_late_axis_adapter",
        domain="extreme",
        purpose=(
            "Adapt canonical Champion Point, potion-family, passive-rank, and two-bar "
            "skill frontiers into ordered indexed search axes and assemble their final state."
        ),
        implementation_path="services.extreme_sustained_dps_generated_late_axis_adapter_service",
        inputs=("ExtremeSustainedDPSCrossAxisContext",),
        outputs=("IndexedFrontierAxes", "ExtremeSustainedDPSGeneratedLateAxisState"),
        dependencies=(
            "extreme.sustained_dps.champion_point_frontier",
            "extreme.sustained_dps.potion_frontier",
            "extreme.sustained_dps.passive_rank_frontier",
            "extreme.sustained_dps.skill_bar_frontier",
            "extreme.sustained_dps.generated_candidate_assembly",
            "extreme.sustained_dps.generated_frontier_wiring",
        ),
        responsibilities=("extreme_sustained_dps_generated_late_axis_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Selections remain separate until all four coordinates exist, then canonical "
            "candidate assembly copies only axis-owned state. Unresolved or empty frontier "
            "denominators fail closed before candidate materialization."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_frontier_wiring",
        domain="extreme",
        purpose=(
            "Wire canonical lazy indexed refinement frontiers into one deterministic "
            "branch-and-bound tree without materializing their Cartesian product."
        ),
        implementation_path="services.extreme_sustained_dps_generated_frontier_wiring_service",
        inputs=("RootState", "IndexedFrontierAxes", "ExactLeafEvaluator", "RequiredDuration"),
        outputs=("ExtremeSustainedDPSGeneratedSearchResult",),
        dependencies=(
            "extreme.sustained_dps.partial_branch_upper_bound",
            "extreme.sustained_dps.generated_branch_and_bound",
        ),
        responsibilities=("extreme_sustained_dps_generated_frontier_wiring",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Owns stable coordinate identity and lazy axis traversal only. Each concrete "
            "frontier still owns legality and indexed materialization; canonical bound providers "
            "and exact Combat Simulation remain external authorities. Dynamic child counts are supported."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_branch_and_bound",
        domain="extreme",
        purpose=(
            "Coordinate proof-safe lazy generated sustained-DPS search with external optimistic "
            "bounds, exact canonical leaf evaluation, incumbent maintenance, tie preservation, "
            "and global-maximum proof bookkeeping."
        ),
        implementation_path="services.extreme_sustained_dps_generated_branch_and_bound_search_service",
        inputs=("GeneratedSearchBranches", "BranchExpander", "ExactLeafEvaluator", "RequiredDuration"),
        outputs=("ExtremeSustainedDPSGeneratedSearchResult",),
        dependencies=("extreme.sustained_dps.pruning",),
        responsibilities=("extreme_sustained_dps_generated_branch_and_bound",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Owns search order and proof bookkeeping only. It never calculates ESO damage or "
            "manufactures bounds. Missing/unproven bounds force branches open; only proven-safe "
            "ceilings strictly below the incumbent may prune. Equal ceilings remain open so ties survive."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.generated_search_evidence_adapter",
        domain="extreme",
        purpose=(
            "Adapt canonical rotation upper-bound results and generated runtime simulation results "
            "into branch-and-bound evidence without strengthening their proof status."
        ),
        implementation_path="services.extreme_sustained_dps_generated_search_evidence_adapter_service",
        inputs=("RotationUpperBoundOrGeneratedRuntimeResult",),
        outputs=("ExtremeSustainedDPSBoundEvidence", "ExtremeSustainedDPSExactLeafEvaluation"),
        dependencies=(
            "extreme.sustained_dps.generated_branch_and_bound",
            "extreme.sustained_dps.generated_runtime_evaluation",
        ),
        responsibilities=("extreme_sustained_dps_generated_search_evidence_adapter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Proof-preserving adapter only: an unproven/missing rotation ceiling stays unproven, "
            "and an incomplete runtime result never becomes an exact modeled-DPS leaf."
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
        service_id="extreme.sustained_dps.heavy_attack_window_discovery",
        domain="extreme",
        purpose=(
            "Probe every scheduled ordinary skill slot through the canonical soft-action duration scheduler to discover the complete finite family of legal 1.8-second fully charged Heavy Attack starts."
        ),
        implementation_path="services.extreme_sustained_dps_heavy_attack_window_discovery_service",
        inputs=(
            "GeneratedRotationCandidate",
            "RotationDurationRules",
            "AbilityPriorities",
            "ReviewedEncounterChannelBlocks",
            "EncounterChannelBlockDenominatorProof",
        ),
        outputs=("ExtremeSustainedDPSHeavyAttackWindowDiscovery",),
        dependencies=(),
        responsibilities=("extreme_sustained_dps_heavy_attack_window_discovery",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Every scheduled skill slot is tested by the same soft-action scheduler used by Rotation Builder, so first casts, due refreshes, same-bar displacement, hard boundaries, and plan horizon are inherited rather than reimplemented. "
            "Encounter demand windows are not guessed to forbid channeling; explicit reviewed channel-block intervals require their own complete denominator proof."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.heavy_attack_policy_frontier",
        domain="extreme",
        purpose=(
            "Enumerate all compatible subsets of fully charged 1.8-second Heavy Attack windows over one generated rotation candidate, using either legacy exact-slot mutation or a canonical scheduler materializer."
        ),
        implementation_path="services.extreme_sustained_dps_heavy_attack_policy_frontier_service",
        inputs=(
            "GeneratedRotationCandidate",
            "ExplicitOrDiscoveredHeavyAttackWindows",
            "OptionalCanonicalSubsetMaterializer",
        ),
        outputs=("ExtremeSustainedDPSHeavyAttackPolicyFrontier",),
        dependencies=("extreme.sustained_dps.rotation_policy_frontier",),
        responsibilities=("extreme_sustained_dps_heavy_attack_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Legacy callers retain conservative exact-slot mutation. Complete Objective #32 traversal supplies the scheduler-backed subset materializer from Heavy Attack window discovery, allowing canonical same-bar displacement/cascade semantics. "
            "Shared full-charge completion evidence must promote every selected heavy; damage remains owned by RotationCandidateHeavyAttackDamageEvidenceService."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.sustained_dps.rotation_policy_frontier",
        domain="extreme",
        purpose=(
            "Enumerate explicit Ultimate-bar choice plus every legal delayed cast/skip sequence "
            "and anchored potion first-use/reuse timing over one generated seed RotationPlan."
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
        dependencies=(
            "extreme.sustained_dps.rotation_plan_frontier",
            "extreme.sustained_dps.delayed_ultimate_policy_frontier",
        ),
        responsibilities=("extreme_sustained_dps_rotation_policy_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("DPS",),
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Ultimate spend and generation evidence remain owned by RotationUltimateService, delayed cast enumeration is owned by the delayed-Ultimate frontier, "
            "and final Ultimate/potion legality remains owned by RotationScheduledActionResourceLegalityService. "
            "Delayed Ultimate timing is closed over the exact seed-plan skill slots; continuous potion offsets remain open."
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
