from pathlib import Path

from ui import build_workspace_tab_layout_fix


def test_builds_tabs_match_coverage_document_mode() -> None:
    source = Path(build_workspace_tab_layout_fix.__file__).read_text(encoding="utf-8")

    assert "self.build_tabs.setDocumentMode(False)" in source


def test_scribed_recipe_editor_precedes_saved_recipe_list() -> None:
    source = Path(build_workspace_tab_layout_fix.__file__).read_text(encoding="utf-8")

    assert 'recipe_editor = getattr(self, "scribed_recipe_editor", None)' in source
    assert 'recipe_list = getattr(self, "scribed_skill_choices", None)' in source
    assert "list_index = scribed_layout.indexOf(recipe_list)" in source
    assert "scribed_layout.insertWidget(max(0, list_index), recipe_editor)" in source
