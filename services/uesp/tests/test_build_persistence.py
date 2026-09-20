from __future__ import annotations

import json

from models.build_model import (
    BuildRoster,
    ChampionPointEntry,
    GearSlot,
    PlayerBuild,
)
from services.build_service import BuildService


def make_roster() -> BuildRoster:
    build = PlayerBuild(
        Name="Jarakeen",
        Gamertag="Jarakeen",
        Race="Breton",
        EsoClass="Warden",
        FrontBarWeapon=GearSlot(
            Set="Master Architect",
            Trait="Precise",
            Enchant="Absorb Magicka",
        ),
        BackBarWeapon=GearSlot(
            Set="Master Architect",
            Trait="Infused",
            Enchant="Weapon Damage",
        ),
        Necklace=GearSlot(
            Set="Spell Power Cure",
            Trait="Infused",
            Enchant="Magicka Recovery",
        ),
        Ring1=GearSlot(
            Set="Spell Power Cure",
            Trait="Infused",
            Enchant="Spell Damage",
        ),
        Ring2=GearSlot(
            Set="Master Architect",
            Trait="Infused",
            Enchant="Spell Damage",
        ),
        ChampionPoints=[ChampionPointEntry(Name="Enlivening Overflow", Points="50")],
        FrontBarSkills=["Combat Prayer", "Illustrious Healing", "Energy Orb", "Wall of Elements", "Aggressive Horn", ""],
        BackBarSkills=["Elemental Susceptibility", "Radiating Regeneration", "Budding Seeds", "Blue Betty", "Healing Thicket", ""],
        Food="Bewitched Sugar Skulls",
        Potion="Essence of Spell Power",
        Notes="Persistence regression fixture",
    )
    build.Armor["Head"] = {
        "Set": "Ozezan the Inferno",
        "Trait": "Divines",
        "Enchant": "Magicka",
        "Weight": "Light",
    }
    build.Armor["Shoulders"] = {
        "Set": "Spaulder of Ruin",
        "Trait": "Divines",
        "Enchant": "Magicka",
        "Weight": "Light",
    }
    return BuildRoster(Members=[build])


def test_build_service_round_trip_preserves_full_build(tmp_path):
    path = tmp_path / "builds.json"
    service = BuildService(path)
    roster = make_roster()

    service.save(roster)
    loaded = service.load()

    original = roster.Members[0]
    build = loaded.Members[0]

    # Canonical identity is additive Phase 14 state. The build content itself must
    # still round-trip exactly, while load exposes stable IDs for downstream pages.
    assert build.PlayerId
    assert build.CharacterId
    assert build.BuildId
    assert build.Name == original.Name
    assert build.Gamertag == original.Gamertag
    assert build.Race == original.Race
    assert build.EsoClass == original.EsoClass
    assert build.Armor == original.Armor
    assert build.FrontBarWeapon == original.FrontBarWeapon
    assert build.BackBarWeapon == original.BackBarWeapon
    assert build.Necklace == original.Necklace
    assert build.Ring1 == original.Ring1
    assert build.Ring2 == original.Ring2
    assert build.ChampionPoints == original.ChampionPoints
    assert build.FrontBarSkills == original.FrontBarSkills
    assert build.BackBarSkills == original.BackBarSkills
    assert build.Food == original.Food
    assert build.Potion == original.Potion
    assert build.Notes == original.Notes
    assert build.Armor["Head"]["Set"] == "Ozezan the Inferno"
    assert build.Armor["Head"]["Weight"] == "Light"
    assert build.FrontBarWeapon.Enchant == "Absorb Magicka"
    assert build.FrontBarSkills[0] == "Combat Prayer"
    assert build.ChampionPoints[0].Points == "50"


def test_build_service_writes_expected_json(tmp_path):
    path = tmp_path / "builds.json"
    service = BuildService(path)
    roster = make_roster()

    service.save(roster)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw == roster.to_dict()
    assert raw["Members"][0]["Armor"]["Head"]["Set"] == "Ozezan the Inferno"


def test_build_service_repeated_saves_are_reliable(tmp_path):
    path = tmp_path / "builds.json"
    service = BuildService(path)
    roster = make_roster()
    stable_ids: tuple[str, str, str] | None = None

    for index in range(10):
        roster.Members[0].Notes = f"save {index}"
        roster.Members[0].Armor["Head"]["Set"] = (
            "Ozezan the Inferno" if index % 2 == 0 else "Spaulder of Ruin"
        )
        service.save(roster)
        loaded = service.load()
        build = loaded.Members[0]

        current_ids = (build.PlayerId, build.CharacterId, build.BuildId)
        assert all(current_ids)
        if stable_ids is None:
            stable_ids = current_ids
        else:
            assert current_ids == stable_ids

        assert build.Notes == roster.Members[0].Notes
        assert build.Armor == roster.Members[0].Armor
        assert build.FrontBarSkills == roster.Members[0].FrontBarSkills
        assert build.BackBarSkills == roster.Members[0].BackBarSkills

        # Feed the canonical identity back through the next save, just as the Builds
        # UI does after an initial load.
        roster = loaded

    assert not list(tmp_path.glob(".builds.json.*.tmp"))


def test_build_service_does_not_turn_invalid_json_into_empty_roster(tmp_path):
    path = tmp_path / "builds.json"
    path.write_text("{not valid json", encoding="utf-8")
    service = BuildService(path)

    try:
        service.load()
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("Invalid build JSON must not silently become an empty roster")
