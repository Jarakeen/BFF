from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_live_raid_exposes_contextual_boss_mechanics_handoff() -> None:
    live = _source("ui/city_live_raid_page.py")
    route = _source("ui/raid_engine_dashboard_support.py")

    assert 'self.boss_mechanics_button = QPushButton("Boss Mechanics")' in live
    assert "bossMechanicsRequested = Signal(str)" in live
    assert "self.bossMechanicsRequested.emit(encounter_id)" in live
    assert "def _open_live_raid_boss_mechanics" in route
    assert 'window.show_page("console:4")' in route
    assert "open_encounter_by_id" in route


def test_mechanics_live_raid_return_is_contextual() -> None:
    mechanics = _source("ui/mechanics_page.py")
    route = _source("ui/raid_engine_dashboard_support.py")

    assert 'QPushButton("← Back to Live Raid")' in mechanics
    assert "self.back_to_live_raid_button.hide()" in mechanics
    assert "def set_live_raid_return_visible" in mechanics
    assert "def _return_to_live_raid" in route
    assert 'window.show_page("live_raid")' in route
    assert "def _hide_live_return_for_sidebar_mechanics" in route
