from models.build_model import BossLoadout, PlayerBuild


def test_player_build_round_trip_does_not_alias_skill_bars_or_armor() -> None:
    original = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
        BackBarSkills=["Energy Orb", "", "", "", "", ""],
    )
    original.Armor["Head"]["Trait"] = "Divines"

    restored = PlayerBuild.from_dict(original.to_dict())
    restored.FrontBarSkills[0] = "Energy Orb"
    restored.BackBarSkills[0] = "Combat Prayer"
    restored.Armor["Head"]["Trait"] = "Infused"

    assert original.FrontBarSkills[0] == "Combat Prayer"
    assert original.BackBarSkills[0] == "Energy Orb"
    assert original.Armor["Head"]["Trait"] == "Divines"


def test_player_build_to_dict_returns_detached_mutable_containers() -> None:
    build = PlayerBuild(
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
    )
    build.Armor["Head"]["Trait"] = "Divines"

    payload = build.to_dict()
    payload["FrontBarSkills"][0] = "Energy Orb"
    payload["Armor"]["Head"]["Trait"] = "Infused"

    assert build.FrontBarSkills[0] == "Combat Prayer"
    assert build.Armor["Head"]["Trait"] == "Divines"


def test_boss_loadout_from_dict_does_not_alias_input_bars() -> None:
    payload = {
        "BossName": "Oaxiltso",
        "FrontBarSkills": ["Combat Prayer", "", "", "", "", ""],
        "BackBarSkills": ["Energy Orb", "", "", "", "", ""],
    }

    loadout = BossLoadout.from_dict(payload)
    loadout.FrontBarSkills[0] = "Energy Orb"
    loadout.BackBarSkills[0] = "Combat Prayer"

    assert payload["FrontBarSkills"][0] == "Combat Prayer"
    assert payload["BackBarSkills"][0] == "Energy Orb"
