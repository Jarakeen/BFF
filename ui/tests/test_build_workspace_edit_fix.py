from pathlib import Path

from ui import build_workspace_edit_fix


def test_edit_tab_uses_existing_page_scroll_surface() -> None:
    source = Path(build_workspace_edit_fix.__file__).read_text(encoding="utf-8")

    assert "old_scroll = self.edit_build_scroll" in source
    assert "old_scroll.deleteLater()" in source
    assert "self.edit_build_scroll = None" in source
    assert "self.edit_build_host = QWidget(edit_tab)" in source
    assert "edit_layout.addWidget(self.edit_build_host, 1)" in source


def test_edit_selector_moves_into_identity_and_heavy_load_is_deferred() -> None:
    source = Path(build_workspace_edit_fix.__file__).read_text(encoding="utf-8")

    assert "identity_card.set_header_action(self.edit_build_selector)" in source
    assert "QTimer.singleShot(0" in source
    assert "self._build_editor_cache" in source


def test_scribed_tab_reads_and_edits_configured_recipe_data() -> None:
    source = Path(build_workspace_edit_fix.__file__).read_text(encoding="utf-8")

    assert "from ui.scribing_support import _recipes_for, _store_recipes" in source
    assert "recipes = list(_recipes_for(build))" in source
    assert "No scribed skills configured for this build yet." in source
    assert '"+ New Scribed Skill"' in source
    assert '"Save Scribed Skill"' in source
    assert "ScribedSkillRecipe(" in source
    assert "_store_recipes(build, recipes)" in source
    assert "_remove_scribed_recipe" in source
