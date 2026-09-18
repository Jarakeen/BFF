from pathlib import Path


def test_rotation_context_stays_on_one_compact_row() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert "context_row = QHBoxLayout()" in source
    assert "context_grid = QGridLayout()" not in source
    assert '("CHARACTER", "user", self.character_combo, 2, 185)' in source
    assert '("DIFFICULTY", "crossed-swords", self.difficulty_combo, 1, 135)' in source


def test_rotation_results_use_locked_icon_navigator_not_raw_tab_bar() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert "self.result_tabs.tabBar().hide()" in source
    assert '("Timeline", "hourglass")' in source
    assert '("Uptime & Resources", "filter")' in source
    assert '("Explanations", "binoculars")' in source
    assert '("Compare", "scales")' in source
    assert '("Save / Export", "download")' in source
    assert 'self.results_locked_label = QLabel("ⓘ  Generate a rotation to unlock results.")' in source
    assert "self._set_results_unlocked(False)" in source
    assert "self._set_results_unlocked(True)" in source


def test_rotation_intent_buttons_have_compact_icon_and_blue_silver_hover_contract() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")
    theme = Path("ui/theme/theme_manager.py").read_text(encoding="utf-8")

    assert "button.setMinimumHeight(104)" in source
    assert "button.setMaximumHeight(112)" in source
    assert 'set_button_icon(button, values["icon"], size=28)' in source
    assert 'QToolButton[rotationIntentChoice="true"]:hover' in theme
    assert "#92AAB5" in theme


def test_page_heading_qss_explicitly_owns_montserrat() -> None:
    base = Path("assets/themes/bff/foundry.qss").read_text(encoding="utf-8")
    theme = Path("ui/theme/theme_manager.py").read_text(encoding="utf-8")

    assert 'QLabel[pageTitle="true"]' in base
    assert 'font-family: "Montserrat";' in base
    assert 'QLabel[pageTitle="true"]' in theme
    assert 'font-family: "Montserrat";' in theme
