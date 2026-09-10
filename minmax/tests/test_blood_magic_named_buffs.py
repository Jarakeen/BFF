from minmax.combat_effect_semantics import GameUpdate
from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId


def test_blood_magic_magicka_window_maps_to_exact_resource_percent():
    effects = effects_for_buff(
        "Blood Magic: Max Magicka",
        game_update=GameUpdate.U50,
    )

    assert len(effects) == 1
    assert effects[0].stat is StatId.MAX_MAGICKA
    assert effects[0].bucket == "resource_percent"
    assert effects[0].value == 0.10


def test_blood_magic_stamina_window_maps_to_exact_resource_percent():
    effects = effects_for_buff(
        "Blood Magic: Max Stamina",
        game_update=GameUpdate.U50,
    )

    assert len(effects) == 1
    assert effects[0].stat is StatId.MAX_STAMINA
    assert effects[0].bucket == "resource_percent"
    assert effects[0].value == 0.10
