from __future__ import annotations

"""Service-catalog descriptors for Extreme MOST Actual Heal search proof."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


EXTREME_ACTUAL_HEAL_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.actual_heal_attribute_projection",
        domain="extreme",
        purpose=(
            "Proof-reduce the complete legal 64-point Health/Magicka/Stamina simplex "
            "to the two pure resource endpoints for reviewed standing MOST Actual Heal."
        ),
        implementation_path="services.extreme_actual_heal_attribute_projection_service",
        inputs=("PlayerBuild", "HealingEntityId", "ExtremeGlobalSearchUniverse"),
        outputs=("ExtremeActualHealAttributeProjectionResult",),
        responsibilities=("extreme_actual_heal_attribute_denominator_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "The complete 2,145-allocation simplex remains the denominator. Projection "
            "fails closed unless every contributing HEAL component is on the reviewed "
            "type-8 highest-resource path with a non-negative resource coefficient."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_gear_denominator",
        domain="extreme",
        purpose=(
            "Assign every canonical gear set one explicit ordinary-H1 disposition and "
            "reconcile accepted rows against the authoritative five-piece candidate pool."
        ),
        implementation_path="services.extreme_actual_heal_gear_denominator_service",
        inputs=("CanonicalGearSetCorpus", "ExtremeActualHealGearSetCandidatePolicy"),
        outputs=("ExtremeActualHealGearDenominatorReport",),
        responsibilities=("extreme_actual_heal_ordinary_gear_denominator",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "The service is proof-only: it does not broaden admission. Every canonical set "
            "is classified as accepted, unresolved, lacking an ordinary five-piece shape, "
            "or reviewed non-positive/irrelevant under the existing H1 objective screen."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_armor_weight_legality",
        domain="extreme",
        purpose=(
            "Resolve physically legal Light/Medium/Heavy options for each H1 armor slot "
            "from canonical named-set piece evidence."
        ),
        implementation_path="services.extreme_actual_heal_armor_weight_legality_service",
        inputs=("PlayerBuild", "CanonicalGearSetPieceEvidence"),
        outputs=("ExtremeActualHealArmorWeightLegalityResult",),
        responsibilities=("extreme_actual_heal_armor_weight_legality",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Named-set slot identity does not prove armor-weight legality. The service "
            "reads gear_set_piece.armor_type in read-only mode and fails closed when "
            "piece evidence is absent or ambiguous."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_armor_weight_frontier",
        domain="extreme",
        purpose=(
            "Enumerate every physically legal armor-weight layout for the current H1 "
            "gear state and retain one deterministic witness per H1-relevant signature."
        ),
        implementation_path="services.extreme_actual_heal_armor_weight_candidate_service",
        inputs=("PlayerBuild", "ExtremeActualHealArmorWeightLegalityResult"),
        outputs=("ExtremeActualHealArmorWeightCandidateResult",),
        dependencies=("extreme.actual_heal_armor_weight_legality",),
        responsibilities=("extreme_actual_heal_armor_weight_frontier",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "The reviewed signature preserves Medium-piece count for Agility/Dexterity "
            "and distinct armor-type count for Undaunted Mettle."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_armor_package_composition",
        domain="extreme",
        purpose=(
            "Compose existing H1 armor-bearing gear-package candidates with their exact "
            "physically legal armor-weight frontiers before canonical event scoring."
        ),
        implementation_path="services.extreme_actual_heal_armor_weight_package_adapter",
        inputs=("BuildCandidate", "ExtremeActualHealArmorWeightCandidateResult"),
        outputs=("BuildCandidate", "ExtremeActualHealArmorWeightPackageAdapterStats"),
        dependencies=("extreme.actual_heal_armor_weight_frontier",),
        responsibilities=("extreme_actual_heal_gear_armor_weight_composition",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Package services retain ownership of set discovery and slot shape. Unresolved "
            "armor-type evidence removes that package from authoritative scoring and remains "
            "visible in cumulative proof diagnostics across optimization passes."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_armor_progression",
        domain="extreme",
        purpose=(
            "Normalize the reviewed non-class passive ranks required by theoretical H1 "
            "armor search without making the ceiling depend on the seed character's purchases."
        ),
        implementation_path="services.extreme_actual_heal_armor_progression_service",
        inputs=("CharacterProgression", "ExtremeHealClassRoute"),
        outputs=("CharacterProgression",),
        responsibilities=("extreme_actual_heal_armor_passive_progression",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Adds canonical max-rank Medium Armor Agility/Dexterity and Undaunted Mettle only. "
            "Canonical armor and Undaunted resolvers continue to own all stat math."
        ),
    ),
)


__all__ = ["EXTREME_ACTUAL_HEAL_SERVICE_DESCRIPTORS"]
