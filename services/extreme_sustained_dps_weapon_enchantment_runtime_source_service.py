from __future__ import annotations

"""Canonical saved-build weapon-enchantment source projection for Objective #32.

This service resolves which enchant source is equipped on each exact weapon slot and
preserves every trait-adjusted CombatEffect consequence. It owns source identity and
provenance only; cadence, cooldown topology, proc timing, and runtime damage application
remain separate services.
"""

from dataclasses import dataclass
import re

from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentRuntimeSource:
    item_id: int
    identity: str
    identity_label: str
    source_label: str
    active_bar: BarId
    source_slot: str
    effects: tuple[CombatEffect, ...]
    weapon_trait: str | None = None
    weapon_quality: str | None = None
    enchantment_tier: str | None = None
    enchantment_quality: str | None = None
    item_level: str | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceResolution:
    sources: tuple[ExtremeSustainedDPSWeaponEnchantmentRuntimeSource, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService:
    """Resolve exact equipped enchant sources without inventing runtime mechanics."""

    def __init__(
        self,
        *,
        repository: object,
        effect_service: object,
    ) -> None:
        if repository is None or effect_service is None:
            raise ValueError(
                "weapon-enchantment runtime source projection requires repository and effect service"
            )
        self.repository = repository
        self.effect_service = effect_service

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _identity(cls, label: str) -> str:
        value = cls._clean(label).casefold()
        return re.sub(r"[^a-z0-9]+", "_", value).strip("_")

    def resolve(
        self,
        build: PlayerBuild,
    ) -> ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceResolution:
        sources: list[ExtremeSustainedDPSWeaponEnchantmentRuntimeSource] = []
        evidence: list[str] = []
        unresolved: list[str] = []

        for bar_name, bar_id in (("front", BarId.FRONT), ("back", BarId.BACK)):
            for slot_index, entry in enumerate(build.active_weapon_slots(bar_name), start=1):
                source_slot = "main_hand" if slot_index == 1 else "off_hand"
                slot_label = f"{bar_name} {source_slot.replace('_', ' ')}"
                saved_label = self._clean(getattr(entry, "Enchant", ""))
                if not saved_label:
                    continue

                matches = tuple(self.repository.find_item_ids_by_label(saved_label))
                if not matches:
                    unresolved.append(
                        f"{slot_label} weapon enchantment label not found in canonical data: {saved_label}"
                    )
                    continue
                if len(matches) != 1:
                    unresolved.append(
                        f"{slot_label} weapon enchantment label is ambiguous ({len(matches)} matches): {saved_label}"
                    )
                    continue

                item_id = int(matches[0])
                identity_label = self._clean(self.repository.get_identity_label(item_id))
                identity = self._identity(identity_label)
                if not identity:
                    unresolved.append(
                        f"{slot_label} weapon enchantment lacks canonical enchant identity: item {item_id}"
                    )
                    continue

                resolved_effects = tuple(
                    self.effect_service.resolve_effects(
                        item_id,
                        weapon_trait=self._clean(getattr(entry, "Trait", "")) or None,
                        weapon_quality=self._clean(getattr(entry, "Quality", "")) or None,
                    )
                )
                if not resolved_effects:
                    unresolved.append(
                        f"{slot_label} weapon enchantment has no canonical combat-effect consequences: {identity_label}"
                    )
                    continue

                source_labels = tuple(
                    dict.fromkeys(
                        self._clean(effect.source)
                        for effect in resolved_effects
                        if self._clean(effect.source)
                    )
                )
                if len(source_labels) != 1:
                    unresolved.append(
                        f"{slot_label} weapon enchantment consequence rows do not share one canonical source label: {identity_label}"
                    )
                    continue

                weapon_trait = self._clean(getattr(entry, "Trait", "")) or None
                weapon_quality = self._clean(getattr(entry, "Quality", "")) or None
                enchantment_tier = self._clean(getattr(entry, "EnchantTier", "")) or None
                enchantment_quality = self._clean(getattr(entry, "EnchantQuality", "")) or None
                item_level = self._clean(getattr(entry, "Level", "")) or None
                source = ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
                    item_id=item_id,
                    identity=identity,
                    identity_label=identity_label,
                    source_label=source_labels[0],
                    active_bar=bar_id,
                    source_slot=source_slot,
                    effects=resolved_effects,
                    weapon_trait=weapon_trait,
                    weapon_quality=weapon_quality,
                    enchantment_tier=enchantment_tier,
                    enchantment_quality=enchantment_quality,
                    item_level=item_level,
                    evidence=(
                        f"{slot_label}: canonical enchant identity={identity_label}",
                        f"{slot_label}: canonical consequence rows={len(resolved_effects)}",
                        f"{slot_label}: weapon trait={weapon_trait or 'unspecified'}",
                        f"{slot_label}: weapon quality={weapon_quality or 'unspecified'}",
                        f"{slot_label}: enchantment tier={enchantment_tier or 'unspecified'}",
                        f"{slot_label}: enchantment quality={enchantment_quality or 'unspecified'}",
                        f"{slot_label}: item level={item_level or 'unspecified'}",
                    ),
                )
                sources.append(source)
                evidence.extend(source.evidence)

        evidence.extend(
            (
                f"Equipped canonical weapon-enchantment sources: {len(sources)}",
                f"Canonical weapon-enchantment consequence rows: {sum(len(row.effects) for row in sources)}",
                "Weapon-enchantment source projection does not infer proc cadence, cooldown topology, or runtime damage application",
            )
        )
        return ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceResolution(
            sources=tuple(sources),
            evidence=tuple(dict.fromkeys(row for row in evidence if row)),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentRuntimeSource",
    "ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceResolution",
    "ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService",
]
