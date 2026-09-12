from __future__ import annotations

"""Service-catalog descriptors for Extreme named-gear proof/search responsibilities."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


EXTREME_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
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
)


__all__ = ["EXTREME_SERVICE_DESCRIPTORS"]
