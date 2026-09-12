from minmax.base_character_state import BaseCharacterState
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.damage_done import DamageDoneModifiers
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_saved_build_dd_conditional_damage_done_service import (
    RotationSavedBuildDDConditionalDamageDoneResolution,
)
from services.rotation_saved_build_dd_damage_done_service import (
    RotationSavedBuildDDDamageDoneResolution,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService


class _ProgressionAdapter:
    def resolve(self, _build):
        return SavedBuildProgressionResolution(
            character_id="ryl-1",
            progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
            unresolved=(),
        )


class _ContextFactory:
    def build(self, **kwargs):
        return BuildCalculationContext(
            character_id=kwargs["character_id"],
            build_id=kwargs["build_id"],
            progression=kwargs["progression"],
            character_state=BaseCharacterState(
                max_health=20000,
                max_magicka=30000,
                max_stamina=30000,
                health_recovery=500,
                magicka_recovery=1500,
                stamina_recovery=1500,
                traces={},
            ),
            combat_state=kwargs["combat_state"],
            active_bar=kwargs["active_bar"],
            unresolved_gear_effects=(
                "Champion Point effect not yet modeled: Exploiter: Increases your damage done against Off Balance enemies by 2% per stage.",
            ),
        )


class _Unconditional:
    def resolve(self, _build):
        return RotationSavedBuildDDDamageDoneResolution(
            modifiers=DamageDoneModifiers(direct=0.06),
        )


class _Conditional:
    def resolve(self, _build):
        return RotationSavedBuildDDConditionalDamageDoneResolution(
            exploiter_bonus=0.04,
        )


def test_dd_context_carries_exploiter_magnitude_and_retires_stale_static_warning() -> None:
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(),
        context_factory=_ContextFactory(),
        dd_damage_done_service=_Unconditional(),  # type: ignore[arg-type]
        dd_conditional_damage_done_service=_Conditional(),  # type: ignore[arg-type]
    )
    result = service.resolve(
        PlayerBuild(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD")
    )

    assert [context.dd_exploiter_bonus for context in result.contexts] == [0.04, 0.04]
    assert result.resolved is True
    assert result.unresolved == ()
