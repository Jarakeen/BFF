from types import SimpleNamespace

from models.build_model import PlayerBuild
from ui.coverage_health_check_support import (
    _canonical_team_builds,
    select_team_builds,
)


def _build(player, character, build_name, *, ready=False):
    return SimpleNamespace(
        Gamertag=player,
        Name=character,
        BuildName=build_name,
        ReadyForRaid=ready,
        ContextVariants=[],
        to_dict=lambda: {},
    )


def test_health_check_selects_unique_roster_builds_directly():
    members = (
        SimpleNamespace(PlayerName="Jarakeen", CharacterName="Magrat", PrimaryRole="Healer"),
        SimpleNamespace(PlayerName="Rylo", CharacterName="Rylonia", PrimaryRole="Damage"),
    )
    builds = (
        _build("Jarakeen", "Magrat", "DF Healer"),
        _build("Rylo", "Rylonia", "Corpsebuster"),
    )

    selected, unresolved = select_team_builds(builds, members, "Performance Mode")

    assert len(selected) == 2
    assert unresolved == ()
    assert [slot for slot, _build in selected] == ["Healer", "Damage"]


def test_health_check_prefers_one_ready_build_when_character_has_multiple_builds():
    members = (
        SimpleNamespace(PlayerName="Jarakeen", CharacterName="Magrat", PrimaryRole="Healer"),
    )
    builds = (
        _build("Jarakeen", "Magrat", "DF Healer", ready=True),
        _build("Jarakeen", "Magrat", "Experimental Healer", ready=False),
    )

    selected, unresolved = select_team_builds(builds, members, "Performance Mode")

    assert unresolved == ()
    assert len(selected) == 1
    assert selected[0][1].BuildName == "DF Healer"


def test_health_check_refuses_to_guess_between_ambiguous_builds():
    members = (
        SimpleNamespace(PlayerName="Jarakeen", CharacterName="Magrat", PrimaryRole="Healer"),
    )
    builds = (
        _build("Jarakeen", "Magrat", "DF Healer"),
        _build("Jarakeen", "Magrat", "SW Healer"),
    )

    selected, unresolved = select_team_builds(builds, members, "Performance Mode")

    assert selected == ()
    assert unresolved == ("Jarakeen",)


def test_health_check_prefers_exact_canonical_team_build_assignments():
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Role="Healer",
    )
    record = {
        "build_id": "build-1",
        "legacy": build.to_dict(),
    }

    class Catalog:
        def assignments_for_team(self, team_name):
            assert team_name == "Performance Mode"
            return [{
                "build_id": "build-1",
                "raid_role": "Healer",
                "slot_name": "Healer 1",
            }]

        def get_build(self, build_id):
            assert build_id == "build-1"
            return record

    page = SimpleNamespace(
        build_service=SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=Catalog())
        )
    )

    selected, unresolved = _canonical_team_builds(page, "Performance Mode")

    assert unresolved == ()
    assert len(selected) == 1
    assert selected[0][0] == "Healer 1"
    assert selected[0][1].BuildName == "DF Healer"
