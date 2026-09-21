from pathlib import Path
from types import SimpleNamespace

from ui.comp_builder_polish_support import (
    coverage_from_candidate_rows,
    merge_coverage,
)
from ui.components.team_progress_panels import TeamCoverageItem


def _candidate(name: str, *, gear=(), skills=()):
    return SimpleNamespace(
        name=name,
        source_name="Roster",
        eso_class="Necromancer",
        role="Tank",
        gear_sets=tuple(gear),
        skills=tuple(skills),
    )


def test_assigned_builds_feed_visible_buff_debuff_coverage() -> None:
    rows = coverage_from_candidate_rows(
        (
            ("Main Tank", _candidate("Necro Tank", skills=("Glacial Colossus",))),
            ("Healer 1", _candidate("SPC Healer", gear=("Spell Power Cure",))),
        )
    )
    by_name = {row.name: row for row in rows}

    assert by_name["Major Vulnerability"].covered is True
    assert by_name["Major Vulnerability"].provider == "Necro Tank"
    assert by_name["Major Courage"].covered is True
    assert by_name["Major Courage"].provider == "SPC Healer"


def test_assigned_and_declared_coverage_are_merged_without_losing_provider_names() -> None:
    assigned = (
        TeamCoverageItem("Major Courage", "SPC Healer", True),
        TeamCoverageItem("Major Slayer", "", False),
    )
    declared = (
        TeamCoverageItem("Major Courage", "Healer 1", True),
        TeamCoverageItem("Major Slayer", "Support DD", True),
    )

    merged = {row.name: row for row in merge_coverage(assigned, declared)}
    assert merged["Major Courage"].covered is True
    assert merged["Major Courage"].provider == "SPC Healer, Healer 1"
    assert merged["Major Slayer"].covered is True
    assert merged["Major Slayer"].provider == "Support DD"


def test_polish_uses_build_catalog_role_language_and_circle_check_icon() -> None:
    source = Path("ui/comp_builder_polish_support.py").read_text(encoding="utf-8")

    assert 'details.set_title("Selected Player / Build Recommendation")' in source
    assert 'card.set_icon("←")' in source
    assert '"▼ BUILD OPTIONS' in source
    assert "Choose what this player or Recruit slot should run" in source
    assert "Keep the assignment cue in player/slot language" in source
    assert 'icon_label("circle-check", 15)' in source
    assert '"Load the team, select a player or Recruit slot"' in source


def test_polish_is_installed_after_layout() -> None:
    installer = Path("ui/application_team_optimization_bootstrap.py").read_text(encoding="utf-8")

    assert "install_comp_builder_layout()" in installer
    assert "install_comp_builder_polish()" in installer
    assert installer.index("install_comp_builder_layout()") < installer.index(
        "install_comp_builder_polish()"
    )
