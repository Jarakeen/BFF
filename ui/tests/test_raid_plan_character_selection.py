from types import SimpleNamespace

from ui.raid_plan_character_selection_page import (
    known_character_classes,
    known_character_names,
    matching_saved_build_indices,
    raid_plan_stretch_columns,
)


def _build(
    *,
    gamertag: str,
    character: str,
    build_name: str,
    eso_class: str = "Warden",
    player_id: str = "",
    character_id: str = "",
):
    return SimpleNamespace(
        Gamertag=gamertag,
        Name=character,
        BuildName=build_name,
        EsoClass=eso_class,
        PlayerId=player_id,
        CharacterId=character_id,
    )


def _personnel(*, player: str, character: str = "", eso_class: str = ""):
    return SimpleNamespace(PlayerName=player, CharacterName=character, EsoClass=eso_class)


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


def test_character_class_can_come_from_personnel_without_a_saved_build() -> None:
    personnel = [
        _personnel(player="Jarakeen", character="Susan", eso_class="Arcanist"),
    ]

    assert known_character_classes([], personnel, "jarakeen", "SUSAN") == ("Arcanist",)


def test_character_class_does_not_guess_when_sources_conflict() -> None:
    saved_builds = [
        _build(
            gamertag="Jarakeen",
            character="Magrat",
            build_name="Old Import",
            eso_class="Warden",
        )
    ]
    personnel = [
        _personnel(player="Jarakeen", character="Magrat", eso_class="Templar"),
    ]

    assert known_character_classes(saved_builds, personnel, "Jarakeen", "Magrat") == (
        "Templar",
        "Warden",
    )


def test_raid_plan_main_working_columns_fill_available_width() -> None:
    assert raid_plan_stretch_columns() == (1, 2, 3, 4)


def test_matching_saved_builds_prefers_canonical_ids_over_stale_display_names() -> None:
    saved_builds = [
        _build(
            gamertag="Old Alias",
            character="Old Character Label",
            build_name="Canonical Build",
            player_id="player-1",
            character_id="character-1",
        ),
        _build(
            gamertag="Other",
            character="Other Character",
            build_name="Other Build",
            player_id="player-2",
            character_id="character-2",
        ),
    ]

    assert matching_saved_build_indices(
        saved_builds,
        "Current Display Name",
        "Current Character Name",
        player_id="player-1",
        character_id="character-1",
    ) == (0,)


def test_matching_saved_builds_can_use_canonical_player_before_character_is_selected() -> None:
    saved_builds = [
        _build(
            gamertag="Old Alias",
            character="First",
            build_name="One",
            player_id="player-1",
            character_id="character-1",
        ),
        _build(
            gamertag="Old Alias",
            character="Second",
            build_name="Two",
            player_id="player-1",
            character_id="character-2",
        ),
    ]

    assert matching_saved_build_indices(
        saved_builds,
        "Current Display Name",
        player_id="player-1",
    ) == (0, 1)


def test_matching_saved_builds_falls_back_to_same_player_when_character_binding_is_stale() -> None:
    saved_builds = [
        _build(
            gamertag="Rikbacon",
            character="Bacon",
            build_name="Rik — Sorcerer Tank",
            player_id="player-rik",
            character_id="character-bacon",
        ),
        _build(
            gamertag="Someone Else",
            character="Other",
            build_name="Other Build",
            player_id="player-other",
            character_id="character-other",
        ),
    ]

    assert matching_saved_build_indices(
        saved_builds,
        "Rikbacon",
        "Rik",
        player_id="player-rik",
        character_id="stale-personnel-character",
    ) == (0,)


def test_matching_saved_builds_recovers_exact_gamertag_when_player_binding_is_stale() -> None:
    saved_builds = [
        _build(
            gamertag="Rikbacon",
            character="Bacon",
            build_name="Rik — Sorcerer Tank",
            player_id="old-player-rik",
            character_id="character-bacon",
        ),
        _build(
            gamertag="Someone Else",
            character="Bacon",
            build_name="Wrong Player",
            player_id="player-other",
            character_id="character-other",
        ),
    ]

    assert matching_saved_build_indices(
        saved_builds,
        "Rikbacon",
        "Rik",
        player_id="current-player-rik",
        character_id="stale-character-rik",
    ) == (0,)


def test_matching_saved_builds_stale_player_recovery_never_uses_fuzzy_name() -> None:
    saved_builds = [
        _build(
            gamertag="Brainiac",
            character="V.B.",
            build_name="Brainiac — Nightblade Werewolf DD",
            player_id="old-player-brainiac",
            character_id="character-vb",
        ),
    ]

    assert matching_saved_build_indices(
        saved_builds,
        "V Brainiac V",
        "Brainiac",
        player_id="current-player-brainiac",
        character_id="stale-character-brainiac",
    ) == ()
