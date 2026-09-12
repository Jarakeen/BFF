from __future__ import annotations

"""Read-only canonical static evidence snapshot for Extreme max-resource scoring.

The snapshot changes *when* immutable database evidence is loaded, never how ESO
stats are calculated. It owns no objective math, ranking, pruning, or candidate
arithmetic. Canonical scorers continue to consume the same repositories and
mechanics; exhaustive Extreme runs simply reuse one database-scoped evidence graph
instead of rebuilding static readers for every scorer instance.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Callable, TypeVar

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.champion_point_static_repository import (
    ChampionPointRecord,
    ChampionPointStaticRepository,
)
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.racial_passive_stat_repository import RacialPassiveStatRepository
from minmax.skill_line_repository import SkillLineRepository
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillUniverseService,
)


_T = TypeVar("_T")


@dataclass(frozen=True)
class ExtremeResourceCanonicalStaticSnapshot:
    """One process-local canonical evidence snapshot for a specific ESO database."""

    database_path: Path
    armor_glyph_repository: ArmorGlyphEffectRepository
    jewelry_glyph_repository: JewelryGlyphEffectRepository
    jewelry_trait_repository: JewelryTraitRepository
    skill_line_repository: SkillLineRepository
    racial_passive_repository: RacialPassiveStatRepository
    champion_point_repository: ChampionPointStaticRepository
    skill_universe_service: ExtremeSkillUniverseService
    player_skills: tuple[ExtremePlayerSkillRecord, ...]
    champion_points_non_slottable: tuple[ChampionPointRecord, ...]
    champion_points_slottable: tuple[ChampionPointRecord, ...]
    armor_glyph_names: tuple[str, ...]
    jewelry_glyph_names: tuple[str, ...]
    preload_unresolved: tuple[str, ...] = ()

    @property
    def preload_complete(self) -> bool:
        return not self.preload_unresolved


class ExtremeResourceCanonicalStaticSnapshotService:
    """Build/reuse immutable canonical evidence for one exhaustive audit process.

    The cache is keyed by the resolved database path and intentionally lives only
    in the Python process. A new audit process therefore sees a fresh database
    snapshot. Repository objects remain the canonical implementations; the service
    merely gives them the lifetime needed for their existing deterministic caches
    to be useful during exhaustive scoring.
    """

    _CACHE: dict[str, ExtremeResourceCanonicalStaticSnapshot] = {}

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @property
    def cache_key(self) -> str:
        return str(self.database_path.resolve())

    @staticmethod
    def _preload(
        label: str,
        loader: Callable[[], tuple[_T, ...]],
    ) -> tuple[tuple[_T, ...], str | None]:
        try:
            return tuple(loader()), None
        except (sqlite3.Error, OSError) as exc:
            # Snapshot warming is an optimization boundary, not a mechanic owner.
            # Preserve the failure as evidence and leave the canonical repository
            # untouched so later proof/scoring calls still fail closed normally.
            return (), f"Extreme static snapshot preload unavailable [{label}]: {exc}"

    def build(self) -> ExtremeResourceCanonicalStaticSnapshot:
        cached = self._CACHE.get(self.cache_key)
        if cached is not None:
            return cached

        armor_glyph_repository = ArmorGlyphEffectRepository(self.database_path)
        jewelry_glyph_repository = JewelryGlyphEffectRepository(self.database_path)
        jewelry_trait_repository = JewelryTraitRepository(self.database_path)
        skill_line_repository = SkillLineRepository(self.database_path)
        racial_passive_repository = RacialPassiveStatRepository(self.database_path)
        champion_point_repository = ChampionPointStaticRepository(self.database_path)
        skill_universe_service = ExtremeSkillUniverseService(self.database_path)

        unresolved: list[str] = []

        player_skills, error = self._preload(
            "player skills",
            skill_universe_service.all_player_skills,
        )
        if error:
            unresolved.append(error)

        champion_points_non_slottable, error = self._preload(
            "non-slottable champion points",
            champion_point_repository.non_slottable_records,
        )
        if error:
            unresolved.append(error)

        champion_points_slottable, error = self._preload(
            "slottable champion points",
            champion_point_repository.slottable_records,
        )
        if error:
            unresolved.append(error)

        armor_glyph_names, error = self._preload(
            "armor glyph names",
            armor_glyph_repository.list_names,
        )
        if error:
            unresolved.append(error)

        jewelry_glyph_names, error = self._preload(
            "jewelry glyph names",
            jewelry_glyph_repository.list_names,
        )
        if error:
            unresolved.append(error)

        snapshot = ExtremeResourceCanonicalStaticSnapshot(
            database_path=self.database_path.resolve(),
            armor_glyph_repository=armor_glyph_repository,
            jewelry_glyph_repository=jewelry_glyph_repository,
            jewelry_trait_repository=jewelry_trait_repository,
            skill_line_repository=skill_line_repository,
            racial_passive_repository=racial_passive_repository,
            champion_point_repository=champion_point_repository,
            skill_universe_service=skill_universe_service,
            player_skills=player_skills,
            champion_points_non_slottable=champion_points_non_slottable,
            champion_points_slottable=champion_points_slottable,
            armor_glyph_names=armor_glyph_names,
            jewelry_glyph_names=jewelry_glyph_names,
            preload_unresolved=tuple(unresolved),
        )
        self._CACHE[self.cache_key] = snapshot
        return snapshot


__all__ = [
    "ExtremeResourceCanonicalStaticSnapshot",
    "ExtremeResourceCanonicalStaticSnapshotService",
]
