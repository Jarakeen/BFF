from minmax.racial_passive_stat_repository import RacialPassiveStatRepository


def test_racial_utility_passives_are_reviewed_non_max_resource_boundaries(tmp_path):
    repository = RacialPassiveStatRepository(tmp_path / "unused.db")

    cases = {
        "Spell Recharge": (
            "When you activate an ability, you restore 625 Magicka or Stamina, based on whichever is lowest. "
            "This effect can occur once every 6 seconds. When you are using an ability with a channel or cast time, "
            "you take 5% less damage."
        ),
        "Adrenaline Rush": (
            "When you deal damage, you restore 1005 Stamina. This effect can occur once every 5 seconds."
        ),
        "Reveler": (
            "Increases your experience gain with the Two Handed skill line by 15%. "
            "Increases the duration of any consumed drink by 15 minutes."
        ),
        "Wayfarer": (
            "Increases your experience gain with the One Hand and Shield skill line by 15%. "
            "Increases the duration of any eaten food by 15 minutes."
        ),
    }

    for passive_name, tooltip in cases.items():
        stats, boundaries, unresolved = repository._parse_description(passive_name, tooltip)
        assert stats == {}
        assert boundaries
        assert unresolved == []
        assert any("without changing maximum resources" in boundary for boundary in boundaries)
