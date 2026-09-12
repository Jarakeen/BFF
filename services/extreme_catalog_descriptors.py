from __future__ import annotations

"""Service-catalog descriptors for Extreme proof/search responsibilities."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


EXTREME_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.resource_canonical_static_snapshot",
        domain="extreme",
        purpose=(
            "Own one process-local read-only snapshot of canonical database evidence and "
            "repository lifetimes for exhaustive max-resource scoring without duplicating stat math."
        ),
        implementation_path="services.extreme_resource_canonical_static_snapshot_service",
        inputs=("CanonicalEsoDatabase",),
        outputs=("ExtremeResourceCanonicalStaticSnapshot",),
        responsibilities=("extreme_resource_canonical_static_evidence_snapshot",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "This service changes when immutable evidence is loaded, not how a candidate is scored. "
            "Canonical repositories and calculation services remain authoritative; preload failures "
            "stay explicit and a fresh process receives a fresh database snapshot."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_ordinary_named_gear_search",
        domain="extreme",
        purpose=(
            "Find exact ordinary mechanic-complete max-resource named-gear winners "
            "with branch-and-bound and proof-safe partial physical pruning."
        ),
        implementation_path="services.extreme_max_resource_ordinary_named_gear_search_service",
        inputs=(
            "ExtremeGearSetTopologyCatalog",
            "ExtremeGearSetBonusBreakpointCatalog",
            "ExtremeNamedGearSetSlotEligibilityCatalog",
            "ExtremeGearSetObjectiveRelevanceCatalog",
        ),
        outputs=("ExtremeMaxResourceOrdinaryNamedGearSearchResult",),
        dependencies=("extreme.partial_named_gear_physical_feasibility",),
        responsibilities=("extreme_max_resource_ordinary_named_gear_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Search-state mutators, conditional resource effects, and unresolved candidates "
            "remain explicit exclusions until a higher proof layer composes them."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_joint_named_gear_feasibility",
        domain="extreme",
        purpose=(
            "Prove concrete distinct-identity plus physical-slot feasibility before score-ordered "
            "max-resource named-gear search."
        ),
        implementation_path="services.extreme_max_resource_joint_feasibility_search_service",
        inputs=(
            "ExtremeGearSetTopologyCatalog",
            "ExtremeGearSetBonusBreakpointCatalog",
            "ExtremeNamedGearSetSlotEligibilityCatalog",
            "ExtremeGearSetObjectiveRelevanceCatalog",
        ),
        outputs=("ExtremeMaxResourceOrdinaryNamedGearSearchResult",),
        dependencies=(
            "extreme.max_resource_ordinary_named_gear_search",
            "extreme.partial_named_gear_physical_feasibility",
        ),
        responsibilities=("extreme_max_resource_joint_named_gear_feasibility",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Feasibility-only constrained search reorders topology labels but preserves the exact "
            "count multiset; false proves impossibility, true only permits exact score search."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_named_gear_realization_adapter",
        domain="extreme",
        purpose=(
            "Expose exact ordinary Max Magicka and Max Stamina named-gear winners through the "
            "legacy realization contract with canonical dual-bar admissibility proof."
        ),
        implementation_path="services.extreme_max_resource_named_gear_realization_adapter_service",
        inputs=(
            "ExtremeMaxResourceOrdinaryNamedGearSearchResult",
            "ExtremeGearSetTopologyCatalog",
            "ExtremeGearSetObjectiveRelevanceCatalog",
        ),
        outputs=("ExtremeObjectiveNamedGearSetCatalogRealizationResult",),
        dependencies=("extreme.max_resource_joint_named_gear_feasibility",),
        responsibilities=("extreme_max_resource_named_gear_realization_adaptation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "This lower-level adapter exposes the ordinary frontier only; production uncapped "
            "resource objectives use the composed candidate adapter after special branches are included."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_special_named_gear_branches",
        domain="extreme",
        purpose=(
            "Classify ordinary-search exclusions for Max Health, Max Magicka, and Max Stamina "
            "into explicit conditional, percentage, bundle, or search-state proof obligations."
        ),
        implementation_path="services.extreme_max_resource_special_named_gear_branch_service",
        inputs=("ExtremeGearSetObjectiveRelevanceCatalog", "ExcludedNamedGearPairs"),
        outputs=("ExtremeMaxResourceSpecialNamedGearBranchResult",),
        dependencies=("extreme.max_resource_ordinary_named_gear_search",),
        responsibilities=("extreme_max_resource_special_named_gear_branch_classification",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Classification is objective-driven and name-agnostic; classification alone does not "
            "score or execute the special branch."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_special_named_gear_execution",
        domain="extreme",
        purpose=(
            "Dispatch classified Max Resource special named-gear obligations to canonical "
            "runtime-condition or search-state execution owners."
        ),
        implementation_path="services.extreme_max_resource_special_named_gear_execution_service",
        inputs=(
            "ExtremeMaxResourceSpecialNamedGearBranchResult",
            "PlayerBuild",
            "ExtremeHealClassRoute",
        ),
        outputs=("ExtremeMaxResourceSpecialNamedGearExecutionResult",),
        dependencies=("extreme.max_resource_special_named_gear_branches",),
        responsibilities=("extreme_max_resource_special_named_gear_execution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Conditional branches reuse candidate runtime-condition materialization; search-state "
            "mutations reuse the canonical execution-coverage owners such as the two-Mundus evaluator."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_named_gear_candidate_search",
        domain="extreme",
        purpose=(
            "Compose exact ordinary Max Resource winners with every legal non-empty special-set "
            "subset while preserving proof-safe physical feasibility and tied ordinary fillers."
        ),
        implementation_path="services.extreme_max_resource_named_gear_candidate_search_service",
        inputs=(
            "ExtremeGearSetTopologyCatalog",
            "ExtremeMaxResourceOrdinaryNamedGearSearchResult",
            "ExtremeMaxResourceSpecialNamedGearBranchResult",
        ),
        outputs=("ExtremeMaxResourceNamedGearCandidateSearchResult",),
        dependencies=(
            "extreme.max_resource_joint_named_gear_feasibility",
            "extreme.max_resource_special_named_gear_branches",
            "extreme.partial_named_gear_physical_feasibility",
        ),
        responsibilities=("extreme_max_resource_named_gear_candidate_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Special mechanics contribute zero to the ordinary filler pruning bound and are scored "
            "later by their canonical runtime or search-axis owner."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_resource_named_gear_candidate_realization_adapter",
        domain="extreme",
        purpose=(
            "Expose the composed ordinary-plus-special Max Resource candidate frontier through the "
            "legacy realization contract with canonical dual-bar admissibility proof."
        ),
        implementation_path="services.extreme_max_resource_named_gear_candidate_realization_adapter_service",
        inputs=(
            "ExtremeMaxResourceNamedGearCandidateSearchResult",
            "ExtremeGearSetTopologyCatalog",
            "ExtremeGearSetObjectiveRelevanceCatalog",
        ),
        outputs=("ExtremeObjectiveNamedGearSetCatalogRealizationResult",),
        dependencies=("extreme.max_resource_named_gear_candidate_search",),
        responsibilities=("extreme_max_resource_named_gear_candidate_realization_adaptation",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Denominator closure requires the composed frontier to remain unchanged under canonical "
            "dual-bar admissibility and to contain no unresolved evidence."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_health_special_named_gear_branches",
        domain="extreme",
        purpose=(
            "Classify ordinary-search exclusions for Max Health into explicit conditional "
            "or search-space-mutation proof obligations."
        ),
        implementation_path="services.extreme_max_health_special_named_gear_branch_service",
        inputs=("ExtremeGearSetObjectiveRelevanceCatalog", "ExcludedNamedGearPairs"),
        outputs=("ExtremeMaxHealthSpecialNamedGearBranchResult",),
        dependencies=("extreme.max_resource_ordinary_named_gear_search",),
        responsibilities=("extreme_max_health_special_named_gear_branch_classification",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Classification is evidence-driven and does not score or execute the special branch."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_health_special_named_gear_execution",
        domain="extreme",
        purpose=(
            "Dispatch classified Max Health special named-gear obligations to the existing "
            "canonical runtime-condition or search-state execution owner."
        ),
        implementation_path="services.extreme_max_health_special_named_gear_execution_service",
        inputs=(
            "ExtremeMaxHealthSpecialNamedGearBranchResult",
            "PlayerBuild",
            "ExtremeHealClassRoute",
        ),
        outputs=("ExtremeMaxHealthSpecialNamedGearExecutionResult",),
        dependencies=("extreme.max_health_special_named_gear_branches",),
        responsibilities=("extreme_max_health_special_named_gear_execution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Conditional branches reuse candidate runtime-condition materialization; "
            "Twice-Born Star reuses the canonical two-Mundus structural evaluator."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.max_health_named_gear_candidate_search",
        domain="extreme",
        purpose=(
            "Compose the ordinary exact Max Health gear winner with every legal non-empty "
            "special-set subset, maximizing only the proven ordinary flat fillers around each subset."
        ),
        implementation_path="services.extreme_max_health_named_gear_candidate_search_service",
        inputs=(
            "ExtremeGearSetTopologyCatalog",
            "ExtremeMaxResourceOrdinaryNamedGearSearchResult",
            "ExtremeMaxHealthSpecialNamedGearBranchResult",
        ),
        outputs=("ExtremeMaxHealthNamedGearCandidateSearchResult",),
        dependencies=(
            "extreme.max_resource_ordinary_named_gear_search",
            "extreme.max_health_special_named_gear_branches",
            "extreme.partial_named_gear_physical_feasibility",
        ),
        responsibilities=("extreme_max_health_named_gear_candidate_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Special mechanics contribute zero to the pruning bound and are scored later by their "
            "canonical runtime or search-axis owner, so the candidate reduction remains optimistic."
        ),
    ),
)


__all__ = ["EXTREME_SERVICE_DESCRIPTORS"]
