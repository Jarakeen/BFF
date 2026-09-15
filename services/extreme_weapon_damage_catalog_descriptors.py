from __future__ import annotations

"""Catalog metadata for the closed Extreme Weapon Damage record."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


EXTREME_WEAPON_DAMAGE_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.weapon_damage_record",
        domain="extreme",
        purpose=(
            "Expose the reviewed U50 contextual potion-active Weapon Damage maximum "
            "and its closed denominator/runtime prerequisites through the canonical Extreme Record contract."
        ),
        implementation_path="services.extreme_weapon_damage_record_service",
        inputs=("ReviewedWeaponDamageConditionalSnapshot",),
        outputs=("ExtremeRecordResult",),
        responsibilities=("extreme_weapon_damage_record",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        provenance=(
            "Phase 13.5 Weapon Damage conditional snapshot closure",
            "U50 named-set, named-buff, class-passive, resource, and equipment legality evidence",
        ),
        notes=(
            "The denominator is proven closed, but the record is intentionally CONDITIONAL because "
            "execute health, Armor of Truth trigger state, potion Major Brutality, Font of Power, "
            "Calculated Defense, Bloodthirsty, and six-slot Expert Mage must coexist."
        ),
    ),
)


__all__ = ["EXTREME_WEAPON_DAMAGE_SERVICE_DESCRIPTORS"]
