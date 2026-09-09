from types import SimpleNamespace

from ui.components.team_progress_panels import (
    compact_provider_label,
    coverage_from_builds,
)


def _build(**overrides):
    values = {
        "Name": "Sorcerer DD Bobs your uncle king of the world and then some",
        "Gamertag": "VeryLongGamertagThatShouldNeverAppearHere",
        "BuildName": "Major Courage support setup with an unnecessarily long title",
        "Role": "Damage Dealer",
        "EsoClass": "Sorcerer",
        "FrontBarSkills": (),
        "BackBarSkills": (),
        "FrontBarWeapon": None,
        "BackBarWeapon": None,
        "Armor": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_compact_provider_label_uses_class_and_role_not_player_name():
    build = _build()

    assert compact_provider_label(build) == "Sorc DD"
    assert "Bobs your uncle" not in compact_provider_label(build)


def test_coverage_provider_uses_compact_build_archetype_label():
    build = _build(BuildName="Major Courage")

    major_courage = next(
        row for row in coverage_from_builds([build]) if row.name == "Major Courage"
    )

    assert major_courage.covered is True
    assert major_courage.provider == "Sorc DD"


def test_compact_provider_label_handles_support_roles():
    assert compact_provider_label(_build(EsoClass="Dragonknight", Role="Tank")) == "DK Tank"
    assert compact_provider_label(_build(EsoClass="Warden", Role="Healer")) == "Warden Healer"
