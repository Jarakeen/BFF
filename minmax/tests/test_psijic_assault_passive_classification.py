from minmax.psijic_assault_passive_classification import (
    ASSAULT_PASSIVES,
    PSIJIC_ORDER_PASSIVES,
    PassiveLayer,
    generic_shared_standing_passives,
)


def test_psijic_order_has_no_generic_shared_standing_passive():
    assert generic_shared_standing_passives() == ()
    assert all(passive.layer != "standing" for passive in PSIJIC_ORDER_PASSIVES)


def test_assault_has_no_generic_shared_standing_passive():
    assert generic_shared_standing_passives() == ()
    assert all(passive.layer != "standing" for passive in ASSAULT_PASSIVES)


def test_known_conditional_layers_are_preserved():
    psijic = {passive.name: passive.layer for passive in PSIJIC_ORDER_PASSIVES}
    assault = {passive.name: passive.layer for passive in ASSAULT_PASSIVES}

    assert psijic["Clairvoyance"] is PassiveLayer.ABILITY_FAMILY
    assert psijic["Concentrated Barrier"] is PassiveLayer.BLOCK_STATE
    assert psijic["Spell Orb"] is PassiveLayer.COMBAT_STATE
    assert assault["Continuous Attack"] is PassiveLayer.EVENT_STATE
    assert assault["Reach"] is PassiveLayer.LOCATION_STATE
    assert assault["Combat Frenzy"] is PassiveLayer.EVENT_STATE
