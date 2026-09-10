from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.alchemy_potion_buff_semantics import (
    U50_POTION_TRAIT_BUFFS,
    U51_POTION_TRAIT_BUFFS,
)
from minmax.gear_set_known_effects import known_effects_for_bonus_row
from minmax.gear_set_repository import GearSetRepository


@dataclass(frozen=True)
class NonAbilityEffectProviderReference:
    """Reviewed non-ability source -> canonical effect relationship."""

    source_kind: str
    source_key: str
    source_name: str
    effect_key: str
    relationship: str
    update: str | None = None
    piece_count: int | None = None
    trigger: str | None = None
    condition: str | None = None
    duration: float | None = None
    cooldown: float | None = None
    target_count: int | None = None
    range: float | None = None
    scaling: str | None = None
    evidence: str = ""


def canonical_identity(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else " " for char in str(value or ""))
    return "_".join(cleaned.casefold().split())


class NonAbilityEffectProviderReferenceService:
    """Read-only provider projection for reviewed gear-set and potion semantics.

    Gear relationships come only from ``gear_set_known_effects`` after the canonical
    GearSetRepository identifies the exact set/bonus row. Potion relationships come
    only from the versioned Alchemy trait semantics tables. Passive providers are not
    projected here because FoundryDock does not yet have one shared reviewed passive
    provider authority.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def gear(self) -> tuple[NonAbilityEffectProviderReference, ...]:
        if not self.database_path.exists():
            return ()

        repository = GearSetRepository(self.database_path)
        try:
            gear_sets = repository.list_sets()
        except sqlite3.Error:
            return ()

        rows: list[NonAbilityEffectProviderReference] = []
        for gear_set in gear_sets:
            try:
                bonuses = repository.get_bonuses(gear_set.id)
            except sqlite3.Error:
                continue
            for bonus in bonuses:
                for known in known_effects_for_bonus_row(
                    bonus.id,
                    bonus.set_id,
                    gear_set.name,
                    bonus.piece_count,
                ):
                    rows.append(
                        NonAbilityEffectProviderReference(
                            source_kind="gear_set",
                            source_key=f"gear_set:{canonical_identity(gear_set.name)}",
                            source_name=gear_set.name,
                            effect_key=canonical_identity(known.name),
                            relationship="Provides",
                            piece_count=known.piece_count,
                            trigger=known.trigger,
                            condition=known.condition,
                            duration=known.duration,
                            cooldown=known.cooldown,
                            target_count=known.target_count,
                            range=known.range,
                            scaling=known.scaling,
                            evidence="Canonical registry: minmax.gear_set_known_effects",
                        )
                    )
        return tuple(sorted(rows, key=lambda row: (row.effect_key, row.source_name.casefold(), row.piece_count or 0)))

    @staticmethod
    def potions() -> tuple[NonAbilityEffectProviderReference, ...]:
        rows: list[NonAbilityEffectProviderReference] = []
        for update, table in (("U50", U50_POTION_TRAIT_BUFFS), ("U51", U51_POTION_TRAIT_BUFFS)):
            for trait, effect_name in table.items():
                rows.append(
                    NonAbilityEffectProviderReference(
                        source_kind="potion_trait",
                        source_key=f"alchemy_trait:{canonical_identity(trait)}",
                        source_name=trait,
                        effect_key=canonical_identity(effect_name),
                        relationship="Grants",
                        update=update,
                        evidence="Canonical module: minmax.alchemy_potion_buff_semantics",
                    )
                )
        return tuple(sorted(rows, key=lambda row: (row.effect_key, row.source_name.casefold(), row.update or "")))

    def all(self) -> tuple[NonAbilityEffectProviderReference, ...]:
        return (*self.gear(), *self.potions())

    def for_effect(self, effect_name: str) -> tuple[NonAbilityEffectProviderReference, ...]:
        wanted = canonical_identity(effect_name)
        if not wanted:
            return ()
        return tuple(row for row in self.all() if row.effect_key == wanted)
