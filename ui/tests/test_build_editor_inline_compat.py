from pathlib import Path

from ui import build_editor_inline_compat


def test_build_workspace_uses_permanent_tabs_without_native_editor_dialog() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    assert "QDialog(" not in source
    assert "dialog.exec(" not in source
    assert 'DARK_SURFACE = "#0C171B"' in source
    assert "QTabWidget" in source
    assert 'tabs.addTab(roster_tab, "Roster")' in source
    assert 'tabs.addTab(edit_tab, "Edit")' in source
    assert 'tabs.addTab(progression_tab, "Character Progression")' in source
    assert 'tabs.addTab(scribed_tab, "Scribed Skills")' in source
    assert "self.edit_button.hide()" in source
    assert "self.splitter.hide()" not in source


def test_edit_tab_selector_tracks_saved_build_index() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    assert 'edit_selector_row.addWidget(QLabel("Character Name"))' in source
    assert "combo.addItem(label, index)" in source
    assert "self.selected_index = index" in source
    assert "self.roster_list.setCurrentRow(index)" in source
    assert "self._build_editor_index = index" in source
    assert "original = self.roster.Members[index]" in source
    assert "self.roster.Members[index] = updated" in source


def test_roster_selection_loads_selected_build_when_edit_tab_is_opened() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    assert "self._syncing_build_selectors = True" in source
    assert "_set_combo_index(combo, self.selected_index)" in source
    assert "if tab_index == 1:" in source
    assert "self._load_edit_tab(index)" in source


def test_progression_and_scribed_workflows_are_embedded_tabs() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    assert "panel.setWindowFlags(Qt.WindowType.Widget)" in source
    assert "self._save_progression_tab()" in source
    assert "self._save_scribed_tab()" in source
    assert '{"Character Progression", "Choose Scribed Skills"}' in source


def test_tabbed_workspace_is_installed_after_other_build_extensions() -> None:
    app_source = (Path(build_editor_inline_compat.__file__).parent.parent / "app.py").read_text(
        encoding="utf-8"
    )

    assert "install_inline_build_editor()" in app_source
    assert app_source.index("install_inline_build_editor()") > app_source.index(
        "install_phase5_potion_picker_support()"
    )
