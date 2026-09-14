from types import SimpleNamespace

from ui.raid_plan_character_selection_page import (
    known_character_names,
    matching_saved_build_indices,
)


def _build(*, gamertag: str, character: str, build_name: str):
    return SimpleNamespace(
        Gamertag=gamertag,
        Name=character,
        BuildName=build_name,
        EsoClass="Warden",
    )


def _personnel(*, player: str, character: str = ""):
    return SimpleNamespace(PlayerName=player, CharacterName=character)


def test_known_character_names_are_scoped_to_selected_player_and_deduplicated() -> None:
    saved_builds = [
        _build(gamertag="Jarakeen", character="Magrat", build_name="DF Healer"),
        _build(gamertag="jarakeen", character="Magrat", build_name="ROJO"),
        _build(gamertag="Jarakeen", character="Nanny", build_name="Tank"),
        _build(gamertag="Rylo", character="Rylonia", build_name="Corpsebuster"),
    ]
    personnel = [
        _personnel(player="Jarakeen", character="Susan"),
        _personnel(player="Rylo", character="Rylonia"),
    ]

    assert known_character_names(saved_builds, personnel, "JARAKEEN") == (
        "Magrat",
        "Nanny",
        "Susan",
    )


def test_matching_saved_builds_narrow_first_by_player_then_character() -> None:
    saved_builds = [
        _build(gamertag="Jarakeen", character="Magrat", build_name="DF Healer"),
        _build(gamertag="Jarakeen", character="Magrat", build_name="ROJO"),
        _build(gamertag="Jarakeen", character="Nanny", build_name="Tank"),
        _build(gamertag="Rylo", character="Magrat", build_name="Different Player"),
    ]

    assert matching_saved_build_indices(saved_builds, "Jarakeen") == (0, 1, 2)
    assert matching_saved_build_indices(saved_builds, "jarakeen", "MAGRAT") == (0, 1)
    assert matching_saved_build_indices(saved_builds, "Rylo", "Magrat") == (3,)
    assert matching_saved_build_indices(saved_builds, "Unknown") == ()
