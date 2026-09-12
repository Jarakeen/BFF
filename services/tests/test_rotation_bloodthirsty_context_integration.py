from minmax.base_character_state import BaseCharacterState
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.damage_done import DamageDoneModifiers
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_saved_build_bloodthirsty_service import (
    RotationBloodthirstySource,
    RotationSavedBuildBloodthirstyResolution,
)
from services.rotation_saved_build_charged_status_chance_service import (
    RotationSavedBuildChargedStatusChanceResolution,
)
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
                "Necklace jewelry trait not yet resolved: Bloodthirsty",
                "Ring 1 jewelry trait not yet resolved: Bloodthirsty",
                "Ring 2 jewelry trait not yet resolved: Bloodthirsty",
            ),
        )


class _Unconditional:
    def resolve(self, _build):
        return RotationSavedBuildDDDamageDoneResolution(modifiers=DamageDoneModifiers())


class _Conditional:
    def resolve(self, _build):
        return RotationSavedBuildDDConditionalDamageDoneResolution(exploiter_bonus=0.0)


class _Charged:
    def resolve(self, _build, *, bars=("front", "back")):
        return RotationSavedBuildChargedStatusChanceResolution()


class _Bloodthirsty:
    def resolve(self, _build):
        return RotationSavedBuildBloodthirstyResolution(
            sources=(
                RotationBloodthirstySource("Necklace", 350.0, "Gold", "CP160"),
                RotationBloodthirstySource("Ring 1", 350.0, "Gold", "CP160"),
                RotationBloodthirstySource("Ring 2", 350.0, "Gold", "CP160"),
            )
        )


def test_dd_context_carries_bloodthirsty_ceiling_and_retires_static_placeholders() -> None:
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(),
        context_factory=_ContextFactory(),
        dd_damage_done_service=_Unconditional(),  # type: ignore[arg-type]
        dd_conditional_damage_done_service=_Conditional(),  # type: ignore[arg-type]
        charged_status_chance_service=_Charged(),  # type: ignore[arg-type]
        bloodthirsty_service=_Bloodthirsty(),  # type: ignore[arg-type]
    )

    result = service.resolve(
        PlayerBuild(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD")
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert [
        context.dd_bloodthirsty_max_weapon_spell_damage for context in result.contexts
    ] == [1050.0, 1050.0]
