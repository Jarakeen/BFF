from pathlib import Path

from services.minmax.gear_set_effect_service import GearSetEffectService
from services.minmax.gear_set_effect_resolver import GearSetEffectResolver
from services.minmax.gear_set_repository import GearSetRepository
from services.minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

VESTMENTS_OF_THE_WARLOCK_ID = 19
WITCHMAN_ARMOR_ID = 20
AKAVIRI_DRAGONGUARD_ID = 21
ARCHERS_MIND_ID = 23


def service() -> GearSetEffectService:
    return GearSetEffectService(
        repository=GearSetRepository(DB_PATH),
        resolver=GearSetEffectResolver(),
    )


def stats(effects):
    return [(effect.stat, effect.value) for effect in effects]


def test_zero_pieces_produces_no_effects():
    effects = service().resolve_effects(
        VESTMENTS_OF_THE_WARLOCK_ID,
        0,
    )

    assert effects == []


def test_two_piece_set_resolves_only_two_piece_bonus():
    effects = service().resolve_effects(
        VESTMENTS_OF_THE_WARLOCK_ID,
        2,
    )

    assert stats(effects) == [
        (StatId.MAGICKA_RECOVERY, 129.0),
    ]


def test_three_piece_set_resolves_two_and_three_piece_bonuses():
    effects = service().resolve_effects(
        VESTMENTS_OF_THE_WARLOCK_ID,
        3,
    )

    assert stats(effects) == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.MAX_MAGICKA, 1096.0),
    ]


def test_four_piece_set_resolves_two_three_and_four_piece_bonuses():
    effects = service().resolve_effects(
        VESTMENTS_OF_THE_WARLOCK_ID,
        4,
    )

    assert stats(effects) == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.MAX_MAGICKA, 1096.0),
        (StatId.MAGICKA_RECOVERY, 129.0),
    ]


def test_five_piece_proc_is_not_guessed():
    effects = service().resolve_effects(
        VESTMENTS_OF_THE_WARLOCK_ID,
        5,
    )

    assert stats(effects) == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.MAX_MAGICKA, 1096.0),
        (StatId.MAGICKA_RECOVERY, 129.0),
    ]


def test_witchman_three_piece_resolves_static_bonuses():
    effects = service().resolve_effects(
        WITCHMAN_ARMOR_ID,
        3,
    )

    assert stats(effects) == [
        (StatId.STAMINA_RECOVERY, 129.0),
        (StatId.WEAPON_DAMAGE, 129.0),
        (StatId.SPELL_DAMAGE, 129.0),
    ]


def test_akaviri_four_piece_resolves_all_static_bonuses():
    effects = service().resolve_effects(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    assert stats(effects) == [
        (StatId.MAGICKA_RECOVERY, 129.0),
        (StatId.HEALING_TAKEN, 4.0),
        (StatId.MAX_HEALTH, 1206.0),
    ]


def test_archers_mind_five_piece_includes_all_active_bonuses():
    effects = service().resolve_effects(
        ARCHERS_MIND_ID,
        5,
    )

    assert len(effects) == 7

    assert [
        (
            effect.stat,
            effect.value,
            effect.condition,
        )
        for effect in effects
    ] == [
        (StatId.MAX_STAMINA, 1096.0, None),
        (StatId.CRITICAL_CHANCE, 657.0, None),
        (StatId.CRITICAL_CHANCE, 657.0, None),
        (StatId.CRITICAL_DAMAGE, 8.0, None),
        (StatId.HEALING_DONE, 8.0, None),
        (StatId.CRITICAL_DAMAGE, 16.0, "sneaking_or_invisible"),
        (StatId.HEALING_DONE, 16.0, "sneaking_or_invisible"),
    ]


def test_use_max_value_false_uses_minimum_range_values():
    effects = service().resolve_effects(
        VESTMENTS_OF_THE_WARLOCK_ID,
        3,
        use_max_value=False,
    )

    assert stats(effects) == [
        (StatId.MAGICKA_RECOVERY, 3.0),
        (StatId.MAX_MAGICKA, 25.0),
    ]