from pathlib import Path

from services.raid_section_state_service import RaidSectionStateService


def test_live_raid_map_link_is_scoped_by_plan_and_encounter(tmp_path):
    state = RaidSectionStateService(tmp_path / "raid_section_state.json")

    state.set_linked_raid_map_id("plan-a", "lokkestiiz", "map-1")
    state.set_linked_raid_map_id("plan-a", "nahviintaas", "map-2")
    state.set_linked_raid_map_id("plan-b", "lokkestiiz", "map-3")

    assert state.linked_raid_map_id("plan-a", "lokkestiiz") == "map-1"
    assert state.linked_raid_map_id("plan-a", "nahviintaas") == "map-2"
    assert state.linked_raid_map_id("plan-b", "lokkestiiz") == "map-3"

    state.set_linked_raid_map_id("plan-a", "lokkestiiz", "")
    assert state.linked_raid_map_id("plan-a", "lokkestiiz") == ""


def test_live_raid_has_split_assignments_and_raid_map_actions():
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Assignments")' in source
    assert 'QPushButton("Raid Map ▾")' in source
    assert "def _link_raid_map" in source
    assert "def _open_linked_raid_map" in source
    assert "def _clear_raid_map_link" in source
    assert "raidMapRequested = Signal(str, str)" in source


def test_mechanics_supports_exact_linked_map_handoff():
    source = Path("ui/mechanics_boss_map_support.py").read_text(encoding="utf-8")
    route = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert "def _open_exact_raid_map" in source
    assert "MechanicsPage.open_exact_raid_map = _open_exact_raid_map" in source
    assert "def _open_live_raid_map" in route
    assert 'window.show_page("console:4")' in route
    assert "live_raid.raidMapRequested.connect" in route
