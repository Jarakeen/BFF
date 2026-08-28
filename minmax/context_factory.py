from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import BaseCharacterCalculator
from .build_calculation_context import BuildCalculationContext, CombatEnvironment
from .character_progression import AttributeAllocation, CharacterProgression


class BuildCalculationContextFactory:
    """Create one calculation snapshot from a canonical build and character state."""

    def __init__(self, calculator: BaseCharacterCalculator | None = None) -> None:
        self.calculator = calculator or BaseCharacterCalculator()

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
        state = self.calculator.calculate(attributes=attributes)
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
