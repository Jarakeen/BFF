from __future__ import annotations

"""Catalog metadata for the closed Extreme Spell Damage record."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


EXTREME_SPELL_DAMAGE_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.spell_damage_record",
        domain="extreme",
        purpose=(
            "Expose the reviewed U50 contextual potion-active Spell Damage maximum "
            "and its closed denominator/runtime prerequisites through the canonical Extreme Record contract."
        ),
        implementation_path="services.extreme_spell_damage_record_service",
        inputs=("ReviewedSpellDamageConditionalSnapshot",),
        outputs=("ExtremeRecordResult",),
        responsibilities=("extreme_spell_damage_record",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        provenance=(
            "Phase 13.5 Spell Damage conditional snapshot replay",
            "U50 Weapon/Spell parity, named-set, named-buff, class-passive, resource, and equipment legality evidence",
        ),
        notes=(
            "The denominator is proven closed, but the record is intentionally CONDITIONAL because "
            "execute health, Armor of Truth trigger state, external Minor Sorcery, potion Major Sorcery, "
            "Font of Power, Calculated Defense, Bloodthirsty, and six-slot Expert Mage must coexist."
        ),
    ),
)


__all__ = ["EXTREME_SPELL_DAMAGE_SERVICE_DESCRIPTORS"]
