from pathlib import Path

from minmax.build import Build
from minmax.build_effect_service import BuildEffectService
from minmax.effects import Effect, EffectOperation
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_effect_service import GearSetEffectService
from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

AKAVIRI_DRAGONGUARD_ID = 21
ARCHERS_MIND_ID = 23


def service() -> BuildEffectService:
    repository = GearSetRepository(DB_PATH)

    gear_set_service = GearSetEffectService(
        repository=repository,
        resolver=GearSetEffectResolver(),
    )

    return BuildEffectService(
        gear_set_effect_service=gear_set_service,
    )


def test_empty_build_has_no_resolved_effects():
    build = Build()

    effects = service().resolve_effects(build)

    assert effects == []


def test_explicit_build_effects_are_preserved():
    build = Build()

    explicit_effect = Effect(
        operation=EffectOperation.ADD,
        value=500,
        source="Test Effect",
        stat=StatId.MAX_HEALTH,
    )

    build.add_effect(explicit_effect)

    effects = service().resolve_effects(build)

    assert effects == [explicit_effect]


def test_gear_set_effects_are_resolved_from_build():
    build = Build()

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    effects = service().resolve_effects(build)

    assert [
        (effect.stat, effect.value)
        for effect in effects
    ] == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.HEALING_TAKEN, 4.0),
        (StatId.MAX_HEALTH, 1206.0),
    ]


def test_explicit_and_gear_effects_are_combined():
    build = Build()

    explicit_effect = Effect(
        operation=EffectOperation.ADD,
        value=500,
        source="Test Effect",
        stat=StatId.MAX_HEALTH,
    )

    build.add_effect(explicit_effect)

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    effects = service().resolve_effects(build)

    assert len(effects) == 4

    assert effects[0] is explicit_effect

    assert [
        (effect.stat, effect.value)
        for effect in effects[1:]
    ] == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.HEALING_TAKEN, 4.0),
        (StatId.MAX_HEALTH, 1206.0),
    ]


def test_multiple_gear_sets_are_resolved():
    build = Build()

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    build.add_gear_set(
        ARCHERS_MIND_ID,
        2,
    )

    effects = service().resolve_effects(build)

    assert [
        (effect.stat, effect.value)
        for effect in effects
    ] == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.HEALING_TAKEN, 4.0),
        (StatId.MAX_HEALTH, 1206.0),
        (StatId.MAX_STAMINA, 1096.0),
    ]


def test_build_effect_service_does_not_modify_build():
    build = Build()

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    before = list(build.effects)

    service().resolve_effects(build)

    assert build.effects == before