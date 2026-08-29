from __future__ import annotations

from models.build_model import PlayerBuild

from .armor_glyph_repository import ArmorGlyphEffectRepository
from .base_character_state import BaseCharacterCalculator
from .build_calculation_context import BuildCalculationContext, CombatEnvironment
from .character_progression import CharacterProgression
from .core_stat_calculator import CoreStatCalculator
from .gear_set_repository import GearSetRepository
from .gear_stat_inputs import GearCalculationInputs, GearStatInputResolver
from .item_base_stats import BaseItemStatResolver
from .jewelry_glyph_repository import JewelryGlyphEffectRepository
from .jewelry_trait_repository import JewelryTraitRepository
from .mundus_repository import MundusRepository
from .race_repository import RaceRepository
from .static_build_inputs import StaticBuildInputResolver


class BuildCalculationContextFactory:
    """Create one calculation snapshot from a canonical build and character state."""

    def __init__(
        self,
        calculator: BaseCharacterCalculator | None = None,
        core_calculator: CoreStatCalculator | None = None,
        race_repository: RaceRepository | None = None,
        gear_set_repository: GearSetRepository | None = None,
        armor_glyph_repository: ArmorGlyphEffectRepository | None = None,
        jewelry_glyph_repository: JewelryGlyphEffectRepository | None = None,
        jewelry_trait_repository: JewelryTraitRepository | None = None,
        base_item_resolver: BaseItemStatResolver | None = None,
        mundus_repository: MundusRepository | None = None,
    ) -> None:
        self.calculator = calculator or BaseCharacterCalculator()
        self.core_calculator = core_calculator or CoreStatCalculator()
        self.race_repository = race_repository
        self.base_item_resolver = base_item_resolver or BaseItemStatResolver()

        database_path = getattr(gear_set_repository, "database_path", None)
        if gear_set_repository is not None and database_path:
            if armor_glyph_repository is None:
                armor_glyph_repository = ArmorGlyphEffectRepository(database_path)
            if jewelry_glyph_repository is None:
                jewelry_glyph_repository = JewelryGlyphEffectRepository(database_path)
            if jewelry_trait_repository is None:
                jewelry_trait_repository = JewelryTraitRepository(database_path)
            if mundus_repository is None:
                mundus_repository = MundusRepository(database_path)

        self.gear_resolver = (
            GearStatInputResolver(
                gear_set_repository,
                armor_glyph_repository=armor_glyph_repository,
                jewelry_glyph_repository=jewelry_glyph_repository,
                jewelry_trait_repository=jewelry_trait_repository,
            )
            if gear_set_repository is not None
            else None
        )
        self.static_build_resolver = StaticBuildInputResolver(mundus_repository)

    def build(
        self,
        *,
        character_id: str,
        build_id: str,
        build: PlayerBuild,
        progression: CharacterProgression,
        environment: CombatEnvironment = CombatEnvironment.PVE,
        target_type: str = "monster",
        target_count: int = 1,
        target_resistance: float | None = None,
        fight_duration: float | None = None,
        active_bar: str = "front",
    ) -> BuildCalculationContext:
        attributes = progression.attributes
        race_stats = self._race_stats(build.Race)
        gear = self._gear_inputs(build, active_bar=active_bar)

        state = self.calculator.calculate(
            attributes=attributes,
            race_stats=race_stats,
            health=gear.health,
            magicka=gear.magicka,
            stamina=gear.stamina,
            health_recovery=gear.health_recovery,
            magicka_recovery=gear.magicka_recovery,
            stamina_recovery=gear.stamina_recovery,
        )
        core_state = self.core_calculator.calculate(
            character_progression=progression,
            base_character=state,
            race_stats=race_stats,
            inputs=gear.core,
        )
        skills = tuple(skill for skill in (*build.FrontBarSkills, *build.BackBarSkills) if str(skill).strip())
        return BuildCalculationContext(
            character_id=character_id,
            build_id=build_id,
            progression=progression,
            character_state=state,
            core_state=core_state,
            environment=environment,
            target_type=target_type,
            target_count=target_count,
            target_resistance=target_resistance,
            fight_duration=fight_duration,
            selected_skills=skills,
            active_bar=active_bar.casefold(),
            gear_set_counts=gear.set_counts,
            gear_effects_applied=gear.applied_effect_count,
            unresolved_gear_effects=gear.unresolved,
        )

    def _race_stats(self, race_name: str) -> dict[str, float]:
        if self.race_repository is None or not str(race_name).strip():
            return {}
        return self.race_repository.get_stat_map_by_name(str(race_name).strip())

    def _gear_inputs(self, build: PlayerBuild, *, active_bar: str) -> GearCalculationInputs:
        gear = (
            self.gear_resolver.resolve(build, active_bar=active_bar)
            if self.gear_resolver is not None
            else GearCalculationInputs()
        )
        gear = self.base_item_resolver.apply(gear, build, active_bar=active_bar)
        return self.static_build_resolver.apply(gear, build, active_bar=active_bar)
