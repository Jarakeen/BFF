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
    assert lookup("Defensive Stance", "block_cost").layer is BlockModifierLayer.ACTIVE_BAR_SLOT
    assert lookup("Defensive Stance", "block_mitigation").layer is BlockModifierLayer.ACTIVE_BAR_SLOT
    assert lookup("Bracing Anchor", "block_mitigation").layer is BlockModifierLayer.COMBAT_STATE
    assert lookup("Deflect Bolts", "block_mitigation").layer is BlockModifierLayer.DAMAGE_FAMILY


def test_all_current_block_sources_are_marked_implemented_in_their_correct_scope():
    implemented = (
        lookup("Light Armor Penalties", "block_cost"),
        lookup("Medium Armor Bonuses", "block_cost"),
        lookup("Heavy Armor Bonuses", "block_mitigation"),
        lookup("Fortress", "block_cost"),
        lookup("Sword and Board", "block_mitigation"),
        lookup("Defensive Stance", "block_cost"),
        lookup("Defensive Stance", "block_mitigation"),
        lookup("Bracing Anchor", "block_mitigation"),
        lookup("Deflect Bolts", "block_mitigation"),
    )
    assert all("implemented" in entry.stacking_status for entry in implemented)


def test_contextual_sources_remain_scoped_out_of_generic_standing_state():
    bracing_anchor = lookup("Bracing Anchor", "block_mitigation")
    deflect_bolts = lookup("Deflect Bolts", "block_mitigation")

    assert "combat-state" in bracing_anchor.stacking_status
    assert "inactive outside combat" in bracing_anchor.stacking_status
    assert "incoming-attack-family" in deflect_bolts.stacking_status
    assert "excluded from generic melee mitigation" in deflect_bolts.stacking_status
