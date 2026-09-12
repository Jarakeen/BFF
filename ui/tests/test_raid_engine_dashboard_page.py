from pathlib import Path

from ui.raid_engine_dashboard_page import (
    RAID_SLOTS,
    _normalize_slot_name,
    _readiness_score,
)


def test_dashboard_normalizes_raid_chair_names() -> None:
    assert _normalize_slot_name("MainTank") == "Main Tank"
    assert _normalize_slot_name("Off Tank") == "Off Tank"
    assert _normalize_slot_name("Healer2") == "Healer 2"
    assert _normalize_slot_name("DPS 7") == "DD 7"
    assert _normalize_slot_name("DD8") == "DD 8"


def test_dashboard_readiness_improves_with_assignments_and_coverage() -> None:
    empty = _readiness_score(
        assigned=0,
        total_slots=12,
        covered=0,
        total_coverage=15,
        capability_gaps=8,
    )
    partial = _readiness_score(
        assigned=6,
        total_slots=12,
        covered=8,
        total_coverage=15,
        capability_gaps=3,
    )
    ready = _readiness_score(
        assigned=12,
        total_slots=12,
        covered=15,
        total_coverage=15,
        capability_gaps=0,
    )

    assert 0 <= empty < partial < ready == 100
    assert empty == 0  # No team and no static evidence must not look partly ready.


def test_dashboard_declares_exact_twelve_player_trial_shape() -> None:
    assert RAID_SLOTS == (
        "Main Tank",
        "Off Tank",
        "Healer 1",
        "Healer 2",
        "DD 1",
        "DD 2",
        "DD 3",
        "DD 4",
        "DD 5",
        "DD 6",
        "DD 7",
        "DD 8",
    )


def test_dashboard_uses_supplied_decorative_assets_and_wires_all_mockup_destinations() -> None:
    source = Path("ui/raid_engine_dashboard_page.py").read_text(encoding="utf-8")
    support = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert '"assets", "decorative", "raid_engine_oval.png"' in source
    assert '"assets", "decorative", "raid_engine_star.png"' in source
    for route in ("comp_builder", "console:6", "console:7", "console:1", "console:3"):
        assert route in source
    assert "sendTeamRequested.connect(self._send_optimized_team_to_roster)" in support
    assert 'section["page"] = "raid_engine_dashboard"' in support
