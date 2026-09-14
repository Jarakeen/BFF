from __future__ import annotations

"""Service-catalog descriptors for Extreme Health Recovery proof slices.

This module also registers shared Extreme gear-search responsibilities first needed
by the Health Recovery closure work.  Their implementations remain objective-neutral.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


EXTREME_HEALTH_RECOVERY_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.named_gear_armor_weight_realization",
        domain="extreme",
        purpose=(
            "Prove an exact named-set physical witness under an explicit canonical "
            "armor-weight requirement."
        ),
        implementation_path=(
            "services.extreme_named_gear_armor_weight_realization_service"
        ),
        inputs=(
            "ExtremeGearSetCountTopology",
            "ExtremeNamedGearSetSlotEligibility",
            "CanonicalEsoDatabase",
            "RequiredArmorWeight",
        ),
        outputs=("ExtremeNamedGearArmorWeightRealizationResult",),
        responsibilities=("extreme_named_gear_armor_weight_realization",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Named-set armor pieces must support the requested weight; jewelry, "
            "weapons, and unassigned ordinary armor remain distinct physical slots."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.named_gear_armor_weight_filter",
        domain="extreme",
        purpose=(
            "Project canonical named-set slot eligibility through a required armor "
            "weight so ordinary shared realization/search can enforce that weight."
        ),
        implementation_path=(
            "services.extreme_armor_weight_filtered_slot_eligibility_service"
        ),
        inputs=(
            "ExtremeNamedGearSetSlotEligibilityCatalog",
            "CanonicalEsoDatabase",
            "RequiredArmorWeight",
        ),
        outputs=("ExtremeArmorWeightFilteredSlotEligibilityResult",),
        dependencies=("extreme.named_gear_armor_weight_realization",),
        responsibilities=("extreme_named_gear_armor_weight_eligibility_filter",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Armor eligibility is narrowed by canonical armor_type evidence while "
            "jewelry and weapon eligibility remain unchanged."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.constrained_named_gear_exact_flat_search",
        domain="extreme",
        purpose=(
            "Reuse canonical exact-flat named-gear branch-and-bound while requiring "
            "one or more exact named-set breakpoints in every winning witness."
        ),
        implementation_path=(
            "services.extreme_constrained_named_gear_exact_flat_search_service"
        ),
        inputs=(
            "ExtremeGearSetTopologyCatalog",
            "ExtremeGearSetBonusBreakpointCatalog",
            "ExtremeNamedGearSetSlotEligibilityCatalog",
            "ExtremeGearSetObjectiveRelevanceCatalog",
            "ExtremeNamedGearRequirement",
        ),
        outputs=("ExtremeConstrainedNamedGearExactFlatSearchResult",),
        responsibilities=("extreme_constrained_named_gear_exact_flat_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Constraint bonuses are derived search-order devices only and are removed "
            "before objective scores leave the service; unresolved/non-flat required "
            "set semantics fail closed."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.externalized_named_gear_constraint_search",
        domain="extreme",
        purpose=(
            "Prove named-set structural placement while an external mechanic owner "
            "retains the set's conditional, percentage, formula, or runtime semantics."
        ),
        implementation_path=(
            "services.extreme_externalized_named_gear_constraint_search_service"
        ),
        inputs=(
            "ExtremeGearSetTopologyCatalog",
            "ExtremeGearSetBonusBreakpointCatalog",
            "ExtremeNamedGearSetSlotEligibilityCatalog",
            "ExtremeGearSetObjectiveRelevanceCatalog",
            "ExtremeNamedGearRequirement",
            "ExtremeExternalizedNamedGearSemantic",
        ),
        outputs=("ExtremeExternalizedNamedGearConstraintSearchResult",),
        dependencies=("extreme.constrained_named_gear_exact_flat_search",),
        responsibilities=("extreme_externalized_named_gear_constraint_search",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The derived zero-delta relevance view is search-only. Canonical objective "
            "mechanics remain owned and scored by the external semantic service."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.recovery_provisioning_projection",
        domain="extreme",
        purpose=(
            "Reduce the canonical provisioning catalogue to the strongest mapped food "
            "and drink for one Recovery objective without choosing a whole build."
        ),
        implementation_path=(
            "services.extreme_recovery_provisioning_projection_service"
        ),
        inputs=("CanonicalEsoDatabase", "RecoveryObjective"),
        outputs=("ExtremeRecoveryProvisioningProjection",),
        responsibilities=("extreme_recovery_provisioning_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Only canonical static additive Recovery effects are projected; unsupported "
            "operations and ambiguous food/drink identities fail closed."
        ),
    ),
)


__all__ = ["EXTREME_HEALTH_RECOVERY_SERVICE_DESCRIPTORS"]
