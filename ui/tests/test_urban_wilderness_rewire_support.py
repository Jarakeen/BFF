from __future__ import annotations

from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_roster_summary_cards_open_embedded_workspaces() -> None:
    source = _source("ui/city_raid_roster_workspace_page.py")

    assert "QStackedWidget" in source
    assert "_embed_detail_workspaces" in source
    assert 'back = QPushButton("Back to Roster")' in source
    assert "self._embedded_stack.setCurrentIndex(index)" in source
    assert "super()._show_detail(key)" in source


def test_roster_is_streamlined_landing_surface() -> None:
    support = _source("ui/raid_engine_dashboard_support.py")
    sidebar = _source("ui/components/foundry_sidebar.py")

    assert 'window.show_page("roster_workspace")' in support
    assert '("Community News", "community_news")' not in sidebar


def test_raid_plan_uses_static_note_instead_of_hidden_editor() -> None:
    source = _source("ui/city_raid_plan_workspace_page.py")

    assert 'FoundryCard("Plan Note", "feather")' in source
    assert 'QLabel("If it matters, write it down.")' in source
    assert 'FoundryCard("Roles / Spots", "feather")' not in source


def test_assignments_drops_redundant_bottom_field_note_card() -> None:
    source = _source("ui/city_raid_assignments_page.py")

    assert 'FoundryCard("Field Note", "feather")' not in source
    assert 'FoundryCard("Assignment Summary", "group")' in source


def test_readiness_note_art_is_static_and_status_is_not_color_only() -> None:
    source = _source("ui/city_raid_readiness_page.py")

    assert "class _ReadinessArt(QLabel)" in source
    assert "QTimer" not in source
    assert 'return "✓ READY" if value else "! GAP"' in source
    assert 'return "○ NEEDS REVIEW"' in source
    assert '"roster_people.jpg"' in source
    assert '"roster_team.jpg"' in source


def test_urban_collectibles_reuse_etched_badge_art_with_recolor() -> None:
    source = _source("ui/collectibles_new_theme_assets_support.py")

    assert "def field_etched_badge" in source
    assert "source = field_etched_badge(label)" in source
    assert "_CITY_BADGE_TONES" in source
    assert "_recolor_badge" in source
