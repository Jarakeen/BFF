from __future__ import annotations

from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_roster_summary_cards_open_embedded_workspaces() -> None:
    source = _source("ui/city_raid_roster_workspace_page.py")

    assert "QStackedWidget" in source
    assert "_embed_detail_workspaces" in source
    assert 'QPushButton("Back to Roster")' not in source
    assert "back = QToolButton()" in source
    assert 'back.setProperty("rosterBackButton", True)' in source
    assert 'back.setToolTip("Back to Roster")' in source
    assert 'back.setIcon(icon("roster-back"))' in source
    assert "back.clicked.connect(self._show_dashboard)" in source
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


def test_readiness_note_art_is_fixed_field_journal_sketch_and_status_is_not_color_only() -> None:
    source = _source("ui/city_raid_readiness_page.py")

    assert "class _ReadinessArt(QLabel)" in source
    assert "QTimer" not in source
    assert 'return "✓ READY" if value else "! GAP"' in source
    assert 'return "○ NEEDS REVIEW"' in source
    assert '"roster_people.jpg"' in source
    assert '"roster_team.jpg"' in source
    assert '"field_journal", "roster"' in source
    assert '"roster_people.webp"' not in source
    assert '"roster_team.webp"' not in source
    assert "self.setFixedHeight(150)" in source


def test_urban_collectibles_reuse_etched_badge_art_with_recolor() -> None:
    source = _source("ui/collectibles_new_theme_assets_support.py")

    assert "def field_etched_badge" in source
    assert "source = field_etched_badge(label)" in source
    assert "_CITY_BADGE_TONES" in source
    assert "_recolor_badge" in source
    assert 'dashboard.SpriteRef("badges.jpg", 6, 4, index)' in source


def test_teams_and_parchment_notes_do_not_reintroduce_retired_city_roster_art() -> None:
    source = _source("ui/urban_wilderness_accessibility_polish.py")

    assert '"field_journal", "roster", "roster_team.jpg"' in source
    assert '"field_journal", "roster", "roster_people.jpg"' in source
    assert '"roster_team.webp"' not in source
    assert '"roster_people.webp"' not in source
    assert "self.setMinimumHeight(150)" in source
    assert "QSizePolicy.Policy.Expanding" in source
    assert "Parchment/field-journal surfaces use the pencil/sketch family only" in source


def test_raid_map_palette_is_red_green_independent_and_shape_coded() -> None:
    source = _source("ui/urban_wilderness_accessibility_polish.py")

    assert '"Danger": "#B9792F"' in source
    assert '"Safe": "#397A9B"' in source
    assert '"Stack": "#74608E"' in source
    assert '"Danger": Qt.PenStyle.SolidLine' in source
    assert '"Safe": Qt.PenStyle.DashLine' in source
    assert '"Stack": Qt.PenStyle.DotLine' in source
    assert 'outer = QColor("#BDA968" if selected else "#7E7357")' in source


def test_live_raid_notes_are_explicit_editable_state() -> None:
    polish = _source("ui/urban_wilderness_accessibility_polish.py")
    state = _source("services/raid_section_state_service.py")

    assert "QTextEdit" in polish
    assert 'QPushButton("Save Run Notes")' in polish
    assert "self.user_state.set_run_notes" in polish
    assert "def run_notes(" in state
    assert "def set_run_notes(" in state
    assert '"notes": _clean(prior.get("notes"))' in state
