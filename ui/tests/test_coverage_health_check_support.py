from pathlib import Path
from types import SimpleNamespace

from models.build_model import BuildContextVariant, PlayerBuild
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


def _catalog_page(build: PlayerBuild):
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

    return SimpleNamespace(
        build_service=SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=Catalog())
        )
    )


def test_health_check_prefers_exact_canonical_team_build_assignments():
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Role="Healer",
    )

    selected, unresolved = _canonical_team_builds(
        _catalog_page(build),
        "Performance Mode",
    )

    assert unresolved == ()
    assert len(selected) == 1
    assert selected[0][0] == "Healer 1"
    assert selected[0][1].BuildName == "DF Healer"


def test_direct_coverage_uses_base_build_even_when_team_variant_exists():
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Role="Healer",
        Food="Base Food",
        ContextVariants=[
            BuildContextVariant(
                ContextType="Team",
                TeamName="Performance Mode",
                Food="Team Food",
            )
        ],
    )

    selected, unresolved = _canonical_team_builds(
        _catalog_page(build),
        "Performance Mode",
    )

    assert unresolved == ()
    assert selected[0][1].Food == "Base Food"


def test_contextual_coverage_can_apply_team_variant_explicitly():
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Role="Healer",
        Food="Base Food",
        ContextVariants=[
            BuildContextVariant(
                ContextType="Team",
                TeamName="Performance Mode",
                Food="Team Food",
            )
        ],
    )

    selected, unresolved = _canonical_team_builds(
        _catalog_page(build),
        "Performance Mode",
        use_context=True,
    )

    assert unresolved == ()
    assert selected[0][1].Food == "Team Food"


def test_coverage_health_check_helpers_no_longer_inject_roster_team_scopes() -> None:
    source = Path("ui/coverage_health_check_support.py").read_text(encoding="utf-8")

    enhance = source.split("def enhance_coverage_page", 1)[1]
    assert "Coverage's visible selector is owned by the Raid Plan adapter" in enhance
    assert 'combo.addItem(f"Roster Team: {name}", f"roster_team:{name}")' not in enhance
    assert "_sync_team_choices(page)" not in enhance
    assert "Coverage's visible selector is owned by the Raid Plan adapter" in enhance
    assert "trial-specific plan" in enhance


def test_coverage_health_check_keeps_internal_team_audit_helpers_available() -> None:
    source = Path("ui/coverage_health_check_support.py").read_text(encoding="utf-8")

    assert "def select_team_builds(" in source
    assert "def _canonical_team_builds(" in source
    assert "def run_team_health_check(" in source
    assert "parent.setVisible(True)" in source
