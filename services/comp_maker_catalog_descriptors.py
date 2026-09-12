from __future__ import annotations

"""Explicit Comp Maker and Team Optimization service catalog descriptors.

This module contains metadata only. It must not import, instantiate, or execute the
services it describes. Runtime code continues to use typed imports and explicit
dependency wiring.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)
from services.extreme_catalog_descriptors import EXTREME_SERVICE_DESCRIPTORS
from services.rotation_catalog_descriptors import ROTATION_SERVICE_DESCRIPTORS
from services.rotation_dd_periodic_catalog_descriptors import (
    ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS,
)
from services.rotation_gameplay_policy_catalog_descriptors import (
    ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS,
)
from services.rotation_observation_catalog_descriptors import (
    ROTATION_OBSERVATION_SERVICE_DESCRIPTORS,
)
from services.team_prescription_catalog_descriptors import (
    TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS,
)
from services.team_provider_catalog_descriptors import (
    TEAM_PROVIDER_SERVICE_DESCRIPTORS,
)
from services.team_workflow_catalog_descriptors import (
    TEAM_WORKFLOW_SERVICE_DESCRIPTORS,
)


COMP_MAKER_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="comp.builder.build_candidates",
        domain="comp",
        purpose="Merge saved builds and versioned reference templates into deterministic per-chair Comp Maker candidates.",
        implementation_path="services.comp_builder_build_candidates",
        inputs=("PlayerBuild", "TeamPrescriptionTemplate", "ObservedCompositionEvidence"),
        outputs=("CompBuildCandidate",),
        responsibilities=("comp_builder_candidate_discovery",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Ranking is deterministic relevance policy, not canonical combat optimization; missing build fields are never invented.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.provider_evidence",
        domain="comp",
        purpose="Resolve Comp Maker provider identities only through existing canonical raid-coverage and saved-build capability evidence.",
        implementation_path="services.comp_builder_provider_evidence",
        inputs=("CompBuildCandidate", "PlayerBuild", "RaidCoverageProfile"),
        outputs=("CompProviderRequirementResolution", "CanonicalProviderIds"),
        responsibilities=("comp_builder_provider_evidence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Never infers provider identity from gear names, skill names, or prose; unresolved mappings remain unresolved.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.strategy_evidence",
        domain="comp",
        purpose="Evaluate provider-redistribution strategy from canonically proven candidate provider ownership.",
        implementation_path="services.comp_builder_strategy_evidence",
        inputs=("CompBuildCandidate", "CanonicalProviderIds"),
        outputs=("CompStrategyEvidenceResult",),
        dependencies=("comp.builder.provider_evidence",),
        responsibilities=("comp_builder_strategy_evidence",),
        behavior=ServiceBehavior.HEURISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes="Structural strategy evidence is not ESO Logs popularity evidence and gives no credit when provider evidence is unknown.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.team_candidate_optimizer",
        domain="comp",
        purpose="Choose a coherent whole-team assignment from per-chair candidates while preserving hard provider and uniqueness constraints.",
        implementation_path="services.comp_builder_team_candidate_optimizer",
        inputs=("CompTeamCandidatePool", "CanonicalProviderIds", "CompStrategyEvidenceResult"),
        outputs=("CompTeamCandidateOptimizationResult",),
        dependencies=(
            "comp.builder.build_candidates",
            "comp.builder.provider_evidence",
            "comp.builder.strategy_evidence",
        ),
        responsibilities=("comp_builder_whole_team_candidate_optimization",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Hard raid validity outranks composition style; style may choose only among already-legal teams.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.authoritative_prescription",
        domain="comp",
        purpose="Materialize already-selected Comp Maker candidates into the non-destructive PrescribedRoster model without reranking them.",
        implementation_path="services.comp_builder_authoritative_prescription",
        inputs=("CompBuildCandidate", "CompTeamCandidateOptimizationResult"),
        outputs=("PrescribedRoster",),
        dependencies=(
            "comp.builder.build_candidates",
            "comp.builder.team_candidate_optimizer",
        ),
        responsibilities=("comp_builder_authoritative_prescription_materialization",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Whole-team optimizer owns candidate selection; prescription materialization must not rerank candidates.",
    ),
    ServiceDescriptor(
        service_id="team.optimization.canonical_static_analysis",
        domain="team_optimization",
        purpose="Summarize canonical static capability evidence for one selected team without claiming temporal or encounter performance.",
        implementation_path="services.team_optimization_canonical_analysis",
        inputs=("PlayerBuild", "SavedBuildCapabilityAudit"),
        outputs=("TeamOptimizationCanonicalAnalysis",),
        responsibilities=("team_optimization_canonical_static_analysis",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Static capability evidence cannot prove encounter uptime, rotation execution, or raid DPS.",
    ),
    ServiceDescriptor(
        service_id="team.optimization.static_comparison",
        domain="team_optimization",
        purpose="Compare two canonical static team analyses without choosing an encounter-aware raid winner.",
        implementation_path="services.team_optimization_static_comparison",
        inputs=("TeamOptimizationCanonicalAnalysis",),
        outputs=("TeamOptimizationStaticComparison",),
        dependencies=("team.optimization.canonical_static_analysis",),
        responsibilities=("team_optimization_static_comparison",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.POLICY,
        notes="Comparison is bounded to static capability presence, redundancy, gaps, conditional sources, recruits, and evidence boundaries.",
    ),
    *EXTREME_SERVICE_DESCRIPTORS,
    *ROTATION_SERVICE_DESCRIPTORS,
    *ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS,
    *ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS,
    *ROTATION_OBSERVATION_SERVICE_DESCRIPTORS,
    *TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS,
    *TEAM_PROVIDER_SERVICE_DESCRIPTORS,
    *TEAM_WORKFLOW_SERVICE_DESCRIPTORS,
)


__all__ = ["COMP_MAKER_SERVICE_DESCRIPTORS"]
