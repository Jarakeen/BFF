from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from models.build_model import PlayerBuild
from services.extreme_bash_champion_point_service import ExtremeBashChampionPointService
from services.extreme_bash_context_objective_service import (
    ExtremeBashContextObjectiveResult,
    ExtremeBashContextObjectiveService,
)
from services.extreme_bash_deadly_bash_service import ExtremeDeadlyBashService
from services.extreme_bash_jewelry_service import ExtremeBashJewelryService
from services.extreme_bash_objective_service import ExtremeBashDamageInputs
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeBashSavedBuildRecordResult:
    objective: ExtremeBashContextObjectiveResult
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def value(self) -> float:
        return float(self.objective.reviewed_value)

    @property
    def mechanic_complete(self) -> bool:
        return self.objective.mechanic_complete and not self.unresolved


class ExtremeBashSavedBuildRecordService:
    """Evaluate a reviewed Bash lower bound from one saved build.

    Existing canonical owners supply progression, final resistances, dual-bar
    One Hand and Shield legality, Bashing Brutality, Deadly Bash, and equipped
    Bashing jewelry. Formula channels that do not yet have a saved-build owner
    remain ``None`` in ``ExtremeBashDamageInputs`` and therefore survive as
    explicit blockers instead of being silently treated as proved zeroes.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.optimizer = optimizer or ExtremeCompleteOptimizationService(
            database_path=self.database_path
        )
        self.progression = MinmaxCharacterProgressionAdapter(
            self.optimizer.build_service.canonical.catalog_service
        )
        self.cp_repository = ChampionPointStaticRepository(self.database_path)
        self.jewelry = ExtremeBashJewelryService(
            JewelryGlyphEffectRepository(self.database_path),
            JewelryTraitRepository(self.database_path),
        )
        self.deadly_bash = ExtremeDeadlyBashService(self.database_path)

    def evaluate(
        self,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> ExtremeBashSavedBuildRecordResult:
        progression_resolution = self.progression.resolve(build)
        if not progression_resolution.resolved:
            raise ValueError("; ".join(progression_resolution.unresolved))

        progression = progression_resolution.progression
        character_id = progression_resolution.character_id
        build_id = (
            str(getattr(build, "BuildId", "") or "").strip()
            or str(build.BuildName or "").strip()
            or "saved-build"
        )

        champion_point = ExtremeBashChampionPointService.resolve_damage(
            self.cp_repository
        )
        jewelry = self.jewelry.evaluate_build(build)
        deadly_bash = self.deadly_bash.resolve(progression)

        # Context owns resistance. The remaining None channels are deliberate
        # proof boundaries; the Bash objective will retain them as unresolved.
        result = ExtremeBashContextObjectiveService.evaluate_build(
            self.optimizer.context_factory,
            character_id=character_id,
            build_id=f"{build_id}:extreme-bash",
            build=build,
            progression=progression,
            active_bar=active_bar,
            inputs=ExtremeBashDamageInputs(),
            champion_point=champion_point,
            jewelry=jewelry,
        )
        # Deadly Bash belongs to the build-objective layer but the context helper
        # currently does not forward it. Re-evaluate the already-built context is
        # avoided here; preserve that missing bridge explicitly until the shared
        # context adapter accepts the passive evidence directly.
        unresolved = list(result.context_blockers)
        unresolved.extend(result.objective.source_blockers)
        unresolved.extend(
            f"Bash formula channel unresolved: {name}"
            for name in result.objective.objective.unresolved_channels
        )
        unresolved.extend(
            f"Bash legality: {problem}"
            for problem in result.objective.objective.legality_blockers
        )
        if deadly_bash.unresolved:
            unresolved.extend(f"Deadly Bash: {problem}" for problem in deadly_bash.unresolved)
        elif deadly_bash.skill2_bash_damage:
            unresolved.append(
                "Deadly Bash reviewed value exists but saved-build Bash context bridge does not yet forward it"
            )

        evidence = [
            f"Physical Resistance: {result.physical_resistance or 0.0:.0f}",
            f"Spell Resistance: {result.spell_resistance or 0.0:.0f}",
            f"Bashing Brutality stages: {champion_point.stages}",
            f"Equipped jewelry Bash bonus: {jewelry.reviewed_item_extra_bash_damage:.0f}",
        ]
        if deadly_bash.rank is not None:
            evidence.append(f"Deadly Bash rank: {deadly_bash.rank}")

        return ExtremeBashSavedBuildRecordResult(
            objective=result,
            evidence=tuple(evidence),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeBashSavedBuildRecordResult",
    "ExtremeBashSavedBuildRecordService",
]
