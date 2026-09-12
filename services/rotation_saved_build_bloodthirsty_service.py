from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.jewelry_trait_repository import JewelryTraitRepository
from models.build_model import GearSlot, PlayerBuild


@dataclass(frozen=True)
class RotationBloodthirstySource:
    slot_name: str
    max_weapon_spell_damage: float
    quality: str
    level: str


@dataclass(frozen=True)
class RotationSavedBuildBloodthirstyResolution:
    sources: tuple[RotationBloodthirstySource, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    @property
    def total_max_weapon_spell_damage(self) -> float:
        return sum(source.max_weapon_spell_damage for source in self.sources)


class RotationSavedBuildBloodthirstyService:
    """Resolve exact saved jewelry Bloodthirsty ceilings for runtime DD math.

    This service owns only static item magnitude. It does not infer target health,
    execute-phase uptime, or fight progression. Those remain runtime state.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: JewelryTraitRepository | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.repository = repository or JewelryTraitRepository(database)

    @staticmethod
    def _slots(build: PlayerBuild) -> tuple[tuple[str, GearSlot], ...]:
        return (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        )

    def resolve(self, build: PlayerBuild) -> RotationSavedBuildBloodthirstyResolution:
        sources: list[RotationBloodthirstySource] = []
        unresolved: list[str] = []

        for slot_name, slot in self._slots(build):
            if str(slot.Trait or "").strip().casefold() != "bloodthirsty":
                continue

            value = self.repository.get_bloodthirsty_max_damage(
                quality=str(slot.Quality or ""),
                level=str(slot.Level or ""),
            )
            if value is None:
                unresolved.append(
                    f"{slot_name} Bloodthirsty magnitude requires CP160 supported-quality evidence "
                    f"({slot.Level or 'level unset'}, {slot.Quality or 'quality unset'})"
                )
                continue

            sources.append(
                RotationBloodthirstySource(
                    slot_name=slot_name,
                    max_weapon_spell_damage=float(value),
                    quality=str(slot.Quality or ""),
                    level=str(slot.Level or ""),
                )
            )

        return RotationSavedBuildBloodthirstyResolution(
            sources=tuple(sources),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationBloodthirstySource",
    "RotationSavedBuildBloodthirstyResolution",
    "RotationSavedBuildBloodthirstyService",
]
