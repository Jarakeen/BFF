from __future__ import annotations

from dataclasses import dataclass

from minmax.character_progression import CharacterProgression
from minmax.heavy_attack_restoration import (
    HeavyAttackRestorationModifiers,
    HeavyAttackWeaponType,
)
from models.build_model import PlayerBuild


_CYCLE_OF_LIFE_PERCENT_BY_RANK = {
    0: 0.0,
    1: 0.15,
    2: 0.30,
}

_REVITALIZE_PERCENT_PER_HEAVY_PIECE_BY_RANK = {
    0: 0.0,
    1: 0.02,
    2: 0.04,
}


@dataclass(frozen=True)
class HeavyAttackProgressionModifierResolution:
    """Character-owned heavy-attack restoration modifiers.

    This service owns only progression-derived modifiers that can be proven from
    the saved character and equipped armor. Set/runtime/target-state modifiers
    remain separate evidence and must be composed by the caller.
    """

    modifiers: HeavyAttackRestorationModifiers
    heavy_armor_pieces: int
    cycle_of_life_rank: int | None
    revitalize_rank: int | None
    unresolved: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return not self.unresolved


class HeavyAttackProgressionModifierService:
    """Resolve Cycle of Life and Revitalize from explicit character progression.

    Missing progression keys remain unknown. Explicit rank 0 means known
    unpurchased and therefore contributes zero. No role/class inference is used.
    """

    CYCLE_OF_LIFE = "Cycle of Life"
    REVITALIZE = "Revitalize"

    @staticmethod
    def _heavy_armor_pieces(build: PlayerBuild) -> int:
        count = 0
        for entry in build.Armor.values():
            if str(entry.get("Weight", "") or "").strip().casefold() == "heavy":
                count += 1
        return count

    @staticmethod
    def _dedupe(values: list[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        weapon: HeavyAttackWeaponType,
    ) -> HeavyAttackProgressionModifierResolution:
        unresolved: list[str] = []
        heavy_pieces = self._heavy_armor_pieces(build)

        cycle_rank: int | None = None
        cycle_percent = 0.0
        if weapon is HeavyAttackWeaponType.RESTORATION_STAFF:
            cycle_rank = progression.passive_rank(self.CYCLE_OF_LIFE)
            if cycle_rank is None:
                unresolved.append(
                    "Cycle of Life rank is unknown for Restoration Staff heavy restoration"
                )
            elif cycle_rank not in _CYCLE_OF_LIFE_PERCENT_BY_RANK:
                unresolved.append(
                    f"Cycle of Life rank is unsupported: {cycle_rank}"
                )
            else:
                cycle_percent = _CYCLE_OF_LIFE_PERCENT_BY_RANK[cycle_rank]

        revitalize_rank: int | None = None
        revitalize_percent = 0.0
        if heavy_pieces:
            revitalize_rank = progression.passive_rank(self.REVITALIZE)
            if revitalize_rank is None:
                unresolved.append(
                    "Revitalize rank is unknown while Heavy Armor is equipped"
                )
            elif revitalize_rank not in _REVITALIZE_PERCENT_PER_HEAVY_PIECE_BY_RANK:
                unresolved.append(
                    f"Revitalize rank is unsupported: {revitalize_rank}"
                )
            else:
                revitalize_percent = (
                    _REVITALIZE_PERCENT_PER_HEAVY_PIECE_BY_RANK[revitalize_rank]
                    * heavy_pieces
                )

        return HeavyAttackProgressionModifierResolution(
            modifiers=HeavyAttackRestorationModifiers(
                restoration_staff_cycle_of_life_percent=cycle_percent,
                heavy_armor_revitalize_percent=revitalize_percent,
            ),
            heavy_armor_pieces=heavy_pieces,
            cycle_of_life_rank=cycle_rank,
            revitalize_rank=revitalize_rank,
            unresolved=self._dedupe(unresolved),
        )


__all__ = [
    "HeavyAttackProgressionModifierResolution",
    "HeavyAttackProgressionModifierService",
]
