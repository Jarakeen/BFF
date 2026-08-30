from minmax.scaling_rules import ScalingRule


def test_scaling_rules_distinguish_resource_and_attribute_selection():
    assert ScalingRule.HIGHEST_RESOURCE != ScalingRule.HIGHEST_ATTRIBUTE
    assert ScalingRule.HEALTH.value == "health"
    assert ScalingRule.MAGICKA.value == "magicka"
    assert ScalingRule.STAMINA.value == "stamina"


def test_scaling_rules_cover_explicit_and_fixed_scaling():
    assert ScalingRule.FIXED.value == "fixed"
