from minmax.block_modifier_classification import BlockModifierLayer, VERIFIED_BLOCK_MODIFIERS


def lookup(source, stat):
    return next(x for x in VERIFIED_BLOCK_MODIFIERS if x.source == source and x.stat == stat)


def test_block_cost_modifier_values():
    assert lookup("Light Armor Penalties", "block_cost").value == 0.03
    assert lookup("Medium Armor Bonuses", "block_cost").value == -0.03
    assert lookup("Fortress", "block_cost").value == -0.36
    assert lookup("Defensive Stance", "block_cost").value == -0.10


def test_block_mitigation_modifier_values_and_layers():
    assert lookup("Heavy Armor Bonuses", "block_mitigation").value == 0.01
    assert lookup("Sword and Board", "block_mitigation").value == 0.20
    assert lookup("Defensive Stance", "block_mitigation").value == 0.10
    assert lookup("Bracing Anchor", "block_mitigation").layer is BlockModifierLayer.COMBAT_STATE
    assert lookup("Deflect Bolts", "block_mitigation").layer is BlockModifierLayer.DAMAGE_FAMILY


def test_stacking_is_not_claimed_resolved():
    assert all("unresolved" in x.stacking_status or "must not enter" in x.stacking_status for x in VERIFIED_BLOCK_MODIFIERS)
