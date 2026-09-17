from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.champion_point_movement_effects import ChampionPointMovementEffectResolver
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from services.extreme_movement_source_projection_service import (
    ExtremeMovementSourceProjectionService,
)
from services.extreme_movement_state_service import (
    ExtremeMovementStateResult,
    ExtremeMovementStateService,
)


@dataclass(frozen=True)
class ExtremeMovementStaticPackageResult:
    objective_key: str
    result: ExtremeMovementStateResult
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeMovementStaticPackageService:
    """Build a reviewed static lower-bound package for Extreme movement records.

    This package deliberately searches only build-owned static sources whose
    canonical owners already expose exact values: The Steed, three Legendary
    Swift jewelry traits, Celerity, and Wind Chaser for Sprint. Runtime named
    buffs, skills, sets, potions and conditional movement mechanics remain
    explicit unresolved ceiling sources until legal provider search is wired.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        mundus: MundusRepository | None = None,
        jewelry: JewelryTraitRepository | None = None,
        champion_points: ChampionPointStaticRepository | None = None,
    ) -> None:
        self.database_path = str(database_path)
        self.mundus = mundus or MundusRepository(database_path, initialize=False)
        self.jewelry = jewelry or JewelryTraitRepository(database_path)
        self.champion_points = champion_points or ChampionPointStaticRepository(database_path)
        self.cp_movement = ChampionPointMovementEffectResolver(self.champion_points)

    def evaluate(self, objective_key: str) -> ExtremeMovementStaticPackageResult:
        key = str(objective_key or "").strip().casefold()
        if key not in {"movement_speed", "sprint_speed", "stealthed_movement_speed"}:
            raise ValueError(f"Unsupported Extreme movement objective: {objective_key!r}")

        evidence: list[str] = []
        unresolved: list[str] = []

        mundus_effects, mundus_unresolved = self.mundus.effects_for_name("The Steed")
        unresolved.extend(mundus_unresolved)

        item_effects = []
        for slot_name in ("Necklace", "Ring 1", "Ring 2"):
            effects = self.jewelry.get_static_effects(
                "Swift", quality="Legendary", level="CP160"
            )
            if not effects:
                unresolved.append(f"{slot_name}: Legendary CP160 Swift value unavailable")
                continue
            item_effects.extend(effects)
            evidence.append(f"{slot_name}: Legendary Swift")

        cp_effects = []
        for name in (("Celerity",) if key != "sprint_speed" else ("Celerity", "Wind Chaser")):
            record = self.champion_points.get(name)
            if record is None:
                unresolved.append(f"Champion Point not found: {name}")
                continue
            effects, missing = self.cp_movement.resolve(name, record.max_points)
            cp_effects.extend(effects)
            unresolved.extend(missing)
            if effects:
                evidence.append(f"Champion Point: {name} max rank")

        projection = ExtremeMovementSourceProjectionService.compose(
            item_effects=tuple(item_effects),
            mundus_effects=tuple(mundus_effects),
            cp_effects=tuple(cp_effects),
        )
        evidence.extend(projection.evidence)
        unresolved.extend(projection.unresolved)

        if key == "movement_speed":
            unresolved.extend(
                (
                    "Major/Minor Expedition provider search not yet included",
                    "skill and gear-set movement providers not yet included",
                )
            )
        elif key == "sprint_speed":
            unresolved.extend(
                (
                    "Major/Minor Expedition provider search not yet included",
                    "skill, set, and sprint-only provider search not yet exhaustive",
                )
            )
        else:
            unresolved.extend(
                (
                    "stealth penalty-removal and sneak-speed provider search not yet included",
                    "Major/Minor Expedition and other movement providers not yet included",
                )
            )

        result = ExtremeMovementStateService.evaluate(key, projection.inputs)
        return ExtremeMovementStaticPackageResult(
            objective_key=key,
            result=result,
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeMovementStaticPackageResult",
    "ExtremeMovementStaticPackageService",
]
