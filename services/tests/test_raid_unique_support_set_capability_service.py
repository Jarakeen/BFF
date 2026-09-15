from models.build_model import PlayerBuild
from services.raid_unique_support_set_capability_service import (
    RaidUniqueSupportSetCapabilityService,
)
from services.saved_build_capability_service import RaidCoverageSnapshot


def _powerful_assault_backbar_build() -> PlayerBuild:
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        Role="Healer",
    )
    build.Necklace.Set = "Powerful Assault"
    build.Ring1.Set = "Powerful Assault"
    build.Ring2.Set = "Powerful Assault"
    build.BackBarWeapon.Set = "Powerful Assault"
    build.BackBarWeapon.WeaponType = "Ice Staff"
    build.FrontBarWeapon.Set = "Spell Power Cure"
    build.FrontBarWeapon.WeaponType = "Restoration Staff"
    return build


def test_powerful_assault_five_piece_backbar_is_conditional_capability() -> None:
    evidence = RaidUniqueSupportSetCapabilityService().evaluate(
        (_powerful_assault_backbar_build(),)
    )

    powerful_assault = next(
        item for item in evidence if item.effect_name == "Powerful Assault"
    )
    assert powerful_assault.provider == "Magrat"
    assert powerful_assault.state == "conditional"
    assert powerful_assault.qualifying_bars == ("back",)
    assert powerful_assault.front_pieces == 3
    assert powerful_assault.back_pieces == 5


def test_powerful_assault_below_five_pieces_is_not_promoted() -> None:
    build = _powerful_assault_backbar_build()
    build.Ring2.Set = "Spell Power Cure"

    evidence = RaidUniqueSupportSetCapabilityService().evaluate((build,))

    assert all(item.effect_name != "Powerful Assault" for item in evidence)


def test_overlay_promotes_equipped_powerful_assault_from_unverified_to_conditional() -> None:
    snapshot = RaidCoverageSnapshot(
        status={"Powerful Assault": "unverified", "Major Courage": "unverified"},
        providers={"Powerful Assault": [], "Major Courage": []},
        conditional_providers={"Powerful Assault": [], "Major Courage": []},
    )

    result = RaidUniqueSupportSetCapabilityService().overlay(
        snapshot,
        (_powerful_assault_backbar_build(),),
    )

    assert result.status["Powerful Assault"] == "conditional"
    assert result.conditional_providers["Powerful Assault"] == ["Magrat"]
    assert result.status["Major Courage"] == "unverified"


def test_mythic_and_monster_piece_thresholds_are_not_treated_as_five_piece_sets() -> None:
    spaulder = PlayerBuild(Name="Spaulder Healer")
    spaulder.Armor["Shoulders"]["Set"] = "Spaulder of Ruin"

    symphony = PlayerBuild(Name="Symphony Healer")
    symphony.Armor["Head"]["Set"] = "Symphony of Blades"
    symphony.Armor["Shoulders"]["Set"] = "Symphony of Blades"

    evidence = RaidUniqueSupportSetCapabilityService().evaluate((spaulder, symphony))
    by_effect = {(item.effect_name, item.provider): item for item in evidence}

    assert ("Spaulder of Ruin", "Spaulder Healer") in by_effect
    assert ("Symphony of Blades", "Symphony Healer") in by_effect
