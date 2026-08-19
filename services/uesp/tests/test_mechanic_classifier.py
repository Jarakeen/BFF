from services.uesp.mechanic_classifier import classify_mechanic


def test_classifier_extracts_damage_type_and_area_attack():
    result = classify_mechanic("Flame Burst", "Deals flame damage in an area.")
    assert result.damage_type == "flame"
    assert result.mechanic_type == "area_attack"


def test_classifier_extracts_targeted_hazard_and_cleanse():
    result = classify_mechanic(
        "Toxic Pool",
        "Targets two players with a lingering pool. Move away and cleanse the effect.",
    )
    assert result.target_count == 2
    assert result.persistent_hazard is True
    assert result.requires_movement is True
    assert result.requires_cleanse is True
    assert result.mechanic_type == "targeted_hazard"


def test_classifier_extracts_interrupt():
    result = classify_mechanic(
        "Channel",
        "The channel can be interrupted and deals shock damage.",
    )
    assert result.interruptible is True
    assert result.damage_type == "shock"
    assert result.mechanic_type == "interrupt"


def test_classifier_extracts_meaningful_summon_threshold():
    result = classify_mechanic(
        "Summon",
        "When the boss reaches 50% health, it summons a Behemoth.",
    )
    assert result.mechanic_type == "summon"


def test_classifier_extracts_fatal_spread():
    result = classify_mechanic(
        "Curse",
        "Two players must spread or the explosion is fatal.",
    )
    assert result.target_count == 2
    assert result.failure_is_fatal is True
    assert result.mechanic_type == "spread"
