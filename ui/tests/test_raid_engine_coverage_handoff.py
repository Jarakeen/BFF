from pathlib import Path


def test_raid_engine_coverage_navigation_does_not_inject_transient_team_scope() -> None:
    source = Path("ui/raid_engine_dashboard_page.py").read_text(encoding="utf-8")

    method = source.split("def _send_team_to_coverage", 1)[1].split(
        "def _comp_slots", 1
    )[0]
    assert 'self.pageRequested.emit("console:7")' in method
    assert "set_team_scope" not in method
    assert "scope_combo" not in method
    assert "Browse All Saved Builds" not in source
    assert "Open Raid Plan Coverage" in source


def test_coverage_compatibility_team_handoff_refuses_visible_team_scope() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    method = source.split("def set_team_scope", 1)[1].split(
        "def _raid_review_tab", 1
    )[0]
    assert "Coverage no longer exposes transient team scopes" in method
    assert "Coverage evaluates saved Raid Plans only." in method
    assert 'self.scope_combo.addItem("Selected Team"' not in method
