from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.extreme_resource_blood_magic_runtime_context_service import (
    ExtremeResourceBloodMagicRuntimeContextService,
)


class _BloodMagic:
    def __init__(self, resource_stat):
        self.resource_stat = resource_stat

    def resolve(self, **_kwargs):
        return SimpleNamespace(
            branch="resource_window",
            resource_stat=self.resource_stat,
            unresolved=(),
        )


def _progression(*, magicka=0, stamina=0):
    return CharacterProgression(
        attributes=AttributeAllocation(
            health=0,
            magicka=magicka,
            stamina=stamina,
        )
    )


def test_matching_magicka_branch_rebuilds_through_named_buff_layer():
    factory = BuildCalculationContextFactory()
    progression = _progression(magicka=64)
    build = PlayerBuild(EsoClass="Sorcerer", ClassSkillLines=["dark_magic", "daedric_summoning", "storm_calling"])
    base = factory.build(
        character_id="base",
        build_id="base",
        build=build,
        progression=progression,
        active_bar="front",
    )
    service = ExtremeResourceBloodMagicRuntimeContextService(
        blood_magic_service=_BloodMagic("max_magicka")
    )

    context, unresolved, selected = service.resolve(
        factory=factory,
        build=build,
        progression=progression,
        objective_key="max_magicka",
        trigger_ability_name="Dark Exchange",
        character_id="char",
        build_id="build",
    )

    assert unresolved == ()
    assert selected == "max_magicka"
    assert context.combat_state.has_buff("Blood Magic: Max Magicka") is True
    assert context.character_state.max_magicka == pytest.approx(base.character_state.max_magicka * 1.10, abs=1.0)


def test_other_resource_branch_preserves_pre_window_objective_value():
    factory = BuildCalculationContextFactory()
    progression = _progression(magicka=64)
    build = PlayerBuild(EsoClass="Sorcerer", ClassSkillLines=["dark_magic", "daedric_summoning", "storm_calling"])
    service = ExtremeResourceBloodMagicRuntimeContextService(
        blood_magic_service=_BloodMagic("max_stamina")
    )

    context, unresolved, selected = service.resolve(
        factory=factory,
        build=build,
        progression=progression,
        objective_key="max_magicka",
        trigger_ability_name="Dark Exchange",
        character_id="char",
        build_id="build",
    )

    assert unresolved == ()
    assert selected == "max_stamina"
    assert context.combat_state.has_buff("Blood Magic: Max Magicka") is False
    assert context.combat_state.has_buff("Blood Magic: Max Stamina") is False


def test_unsupported_objective_fails_closed():
    service = ExtremeResourceBloodMagicRuntimeContextService(
        blood_magic_service=_BloodMagic("max_magicka")
    )

    with pytest.raises(KeyError, match="unsupported Blood Magic"):
        service.resolve(
            factory=BuildCalculationContextFactory(),
            build=PlayerBuild(),
            progression=CharacterProgression(),
            objective_key="max_health",
            trigger_ability_name="Dark Exchange",
            character_id="char",
            build_id="build",
        )
