from __future__ import annotations

from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from minmax.combat_effect_semantics import GameUpdate


def test_u50_standard_potion_traits_route_to_named_buffs():
    assert potion_buff_for_trait("Restore Health") == "Major Fortitude"
    assert potion_buff_for_trait("Restore Magicka") == "Major Intellect"
    assert potion_buff_for_trait("Restore Stamina") == "Major Endurance"
    assert potion_buff_for_trait("Increase Spell Power") == "Major Sorcery"
    assert potion_buff_for_trait("Increase Weapon Power") == "Major Brutality"
    assert potion_buff_for_trait("Spell Critical") == "Major Prophecy"
    assert potion_buff_for_trait("Weapon Critical") == "Major Savagery"


def test_u51_consolidated_traits_route_to_surviving_named_buffs():
    assert potion_buff_for_trait("Increase Power", game_update=GameUpdate.U51) == "Major Brutality"
    assert potion_buff_for_trait("Critical", game_update=GameUpdate.U51) == "Major Savagery"
    assert potion_buff_for_trait("Increase Spell Power", game_update=GameUpdate.U51) is None
    assert potion_buff_for_trait("Spell Critical", game_update=GameUpdate.U51) is None
