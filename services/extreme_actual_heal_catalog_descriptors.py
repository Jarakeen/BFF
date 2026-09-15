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
            "The current reviewed signature preserves Medium-piece count for Agility/Dexterity "
            "and distinct armor-type count for Undaunted Mettle. Joint gear-package plus "
            "armor-weight search remains a separate E2 proof obligation."
        ),
    ),
)


__all__ = ["EXTREME_ACTUAL_HEAL_SERVICE_DESCRIPTORS"]
