from __future__ import annotations

from models.build_model import PlayerBuild

from .base_character_state import BaseCharacterCalculator
from .build_calculation_context import BuildCalculationContext, CombatEnvironment
from .character_progression import CharacterProgression
from .race_repository import RaceRepository


class BuildCalculationContextFactory:
    """Create one calculation snapshot from a canonical build and character state."""

    def __init__(self, calculator: BaseCharacterCalculator | None = None, race_repository: RaceRepository | None = None) -> None:
        self.calculator = calculator or BaseCharacterCalculator()
        self.race_repository = race_repository

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
    ) -> BuildCalculationContext:
        attributes = progression.attributes
        race_stats = self._race_stats(build.Race)
        state = self.calculator.calculate(attributes=attributes, race_stats=race_stats)
        skills = tuple(skill for skill in (*build.FrontBarSkills, *build.BackBarSkills) if str(skill).strip())
        return BuildCalculationContext(
            character_id=character_id,
            build_id=build_id,
            progression=progression,
            character_state=state,
            environment=environment,
            target_type=target_type,
            target_count=target_count,
            target_resistance=target_resistance,
            fight_duration=fight_duration,
            selected_skills=skills,
        )

    def _race_stats(self, race_name: str) -> dict[str, float]:
        if self.race_repository is None or not str(race_name).strip():
            return {}
        return self.race_repository.get_stat_map_by_name(str(race_name).strip())
