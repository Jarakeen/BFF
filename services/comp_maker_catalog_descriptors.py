from __future__ import annotations

"""Explicit Comp Maker and Team Optimization service catalog descriptors.

This module contains metadata only for the Comp Maker / Team Optimization domain.
Whole-catalog aggregation lives in ``services.service_catalog_aggregator`` so this
family does not transitively own unrelated RaidPlan, Extreme, Rotation, or Team
Workflow descriptor families.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


COMP_MAKER_LOCAL_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="comp.builder.plan_state",
        domain="comp",
        purpose="Own one canonical Comp Maker working state before or after Raid Plan binding and preserve trial-specific planning decisions through finalization/round-trip.",
        implementation_path="services.comp_plan_state_service",
        inputs=("Roster/Assignments Planning Context", "RaidPlan", "CompPlanState", "CompChairState"),
        outputs=("Unbound CompPlanState", "Bound CompPlanState", "RaidPlan"),
        responsibilities=("comp_builder_canonical_working_state",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.POLICY,
        notes="CompPlanState may exist before Raid Plan. Unbound state finalizes directly into a new non-colliding Raid Plan; bound state merges back into the same plan while preserving unrelated fields. Generated-roster draft storage is not part of the supported Phase 14 save path.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.plan_health",
        domain="comp",
        purpose="Evaluate Team Health directly from canonical CompPlanState using shared reviewed planned-gear coverage semantics.",
        implementation_path="services.comp_plan_health_service",
        inputs=("CompPlanState", "PlannedGearCoverageProvider"),
        outputs=("CompPlanHealth", "CompAssignmentHealthReview"),
        dependencies=("comp.builder.plan_state",),
        responsibilities=("comp_builder_team_health",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Planned gear is conditional capability evidence only; assignment ownership remains intent and is reviewed separately from provider proof; runtime uptime and exact slotting remain unproven.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.selected_chair_adviser",
        domain="comp",
        purpose="Compare one explicit build candidate against canonical CompPlanState and explain group-level planning impact before applying it.",
        implementation_path="services.comp_candidate_adviser_service",
        inputs=("CompPlanState", "CompBuildCandidate", "CompPlanHealth"),
        outputs=("CompCandidateProposal", "CompPlanState"),
        dependencies=(
            "comp.builder.plan_state",
            "comp.builder.plan_health",
            "comp.builder.build_candidates",
        ),
        responsibilities=("comp_builder_selected_chair_adviser",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Proposal comparison reports planned coverage, evidence-strength changes, duplicate effects, lock preservation, and unresolved evidence; candidate skills remain evidence-only and runtime uptime belongs downstream.",
    ),
    ServiceDescriptor(
        service_id="comp.builder.plan_autofill",
        domain="comp",
        purpose="Apply whole-team candidate optimization only to unresolved canonical CompPlanState build decisions while preserving locked or already-planned choices.",
        implementation_path="services.comp_plan_autofill_service",
        inputs=("CompPlanState", "CompTeamCandidatePool", "CanonicalProviderIds"),
        outputs=("CompAutoFillResult", "CompPlanState"),
        dependencies=(
            "comp.builder.plan_state",
            "comp.builder.plan_health",
            "comp.builder.team_candidate_optimizer",
        ),
        responsibilities=("comp_builder_canonical_autofill",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes="Auto-Fill Builds never fabricates a player identity for an open Recruit chair, never overwrites locked/existing gear or saved-build choices, and does not adopt observed/candidate skill packages yet.",
    ),
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
)

# Compatibility name retained for callers that historically imported the family
# under this symbol. It is now local-only; whole-catalog aggregation belongs to
# services.service_catalog_aggregator.
COMP_MAKER_SERVICE_DESCRIPTORS = COMP_MAKER_LOCAL_SERVICE_DESCRIPTORS


__all__ = [
    "COMP_MAKER_LOCAL_SERVICE_DESCRIPTORS",
    "COMP_MAKER_SERVICE_DESCRIPTORS",
]
