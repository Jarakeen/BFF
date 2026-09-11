from minmax.racial_passive_stat_repository import RacialPassiveStatRepository


def _repository(tmp_path):
    return RacialPassiveStatRepository(tmp_path / "unused.db")


def test_combined_resource_tooltips_resolve_each_canonical_resource(tmp_path):
    repository = _repository(tmp_path)

    dynamic, boundaries, unresolved = repository._parse_description(
        "Dynamic",
        "Increases your Max Magicka and Max Stamina by 1910.",
    )
    lunar, lunar_boundaries, lunar_unresolved = repository._parse_description(
        "Lunar Blessings",
        "Increase your Maximum Health, Magicka, and Stamina by 915.",
    )

    assert dynamic == {"max_magicka": 1910.0, "max_stamina": 1910.0}
    assert boundaries == []
    assert unresolved == []

    assert lunar == {
        "max_health": 915.0,
        "max_magicka": 915.0,
        "max_stamina": 915.0,
    }
    assert lunar_boundaries == []
    assert lunar_unresolved == []


def test_combined_recovery_and_non_resource_combat_stats_are_mapped(tmp_path):
    repository = _repository(tmp_path)

    robustness, _, robustness_unresolved = repository._parse_description(
        "Robustness",
        "Increases your Health, Magicka, and Stamina Recovery by 90.",
    )
    life_mender, _, life_mender_unresolved = repository._parse_description(
        "Life Mender",
        "Increases your Healing Done by 6%.",
    )
    resist_flame, _, resist_flame_unresolved = repository._parse_description(
        "Resist Flame",
        "Increases your Flame Resistance by 4620.",
    )
    hunters_eye, _, hunters_eye_unresolved = repository._parse_description(
        "Hunter's Eye",
        "Increases your Stealth Detection radius by 3 meters. "
        "Increases your Movement Speed by 5% and your Physical and Spell Penetration by 950.",
    )

    assert robustness == {
        "health_recovery": 90.0,
        "magicka_recovery": 90.0,
        "stamina_recovery": 90.0,
    }
    assert robustness_unresolved == []

    assert life_mender == {"healing_done_percent": 6.0}
    assert life_mender_unresolved == []

    assert resist_flame == {"flame_resistance": 4620.0}
    assert resist_flame_unresolved == []

    assert hunters_eye == {
        "physical_penetration": 950.0,
        "spell_penetration": 950.0,
    }
    assert hunters_eye_unresolved == []


def test_pure_utility_racial_passives_use_existing_noncombat_boundary(tmp_path):
    repository = _repository(tmp_path)

    descriptions = {
        "Amphibian": "Increases your experience gain with the Restoration Staff skill line by 15%. Increases your swimming speed by 50%.",
        "Highborn": "Increases your experience gain with the Destruction Staff skill line by 15%. Increases your experience gained by 1%.",
        "Diplomat": "Increases your experience gain with the One Hand and Shield skill line by 15%. Increases your gold gained by 1%.",
        "Cutpurse": "Increases your experience gain with the Medium Armor skill line by 15%. Increases your chance to successfully pickpocket by 5%.",
        "Craftsman": "Increases your experience gain with the Heavy Armor skill line by 15%. Increases your crafting inspiration gained by 10%.",
    }

    for passive_name, description in descriptions.items():
        stats, boundaries, unresolved = repository._parse_description(passive_name, description)
        assert stats == {}
        assert boundaries == [
            f"Non-combat racial passive outside combat capability audit: {passive_name}"
        ]
        assert unresolved == []


def test_environmental_racial_passives_use_mitigation_boundary(tmp_path):
    repository = _repository(tmp_path)

    descriptions = {
        "Ashlander": "Reduces your damage taken from Lava by 50%.",
        "Acrobat": "Reduces your fall damage taken by 10%.",
    }

    for passive_name, description in descriptions.items():
        stats, boundaries, unresolved = repository._parse_description(passive_name, description)
        assert stats == {}
        assert boundaries == [
            f"Racial environmental-damage mitigation requires mitigation model: {passive_name}"
        ]
        assert unresolved == []


def test_unreviewed_racial_tooltip_still_fails_closed(tmp_path):
    repository = _repository(tmp_path)

    stats, boundaries, unresolved = repository._parse_description(
        "Mystery Heritage",
        "Gain unknowable ancestral benefits whenever the moons approve.",
    )

    assert stats == {}
    assert boundaries == []
    assert unresolved == ["Racial passive tooltip is not yet stat-mapped: Mystery Heritage"]
