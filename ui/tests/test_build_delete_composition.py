from pathlib import Path

from ui import phase5_build_delete_support, themed_builds_page


def test_build_delete_support_uses_instance_composition_not_class_patch() -> None:
    source = Path(phase5_build_delete_support.__file__).read_text(encoding="utf-8")

    assert "def attach_delete_build_action(page)" in source
    assert 'FoundryButton("Delete Build", role=ButtonRole.DANGER)' in source
    assert "BuildsPage._build_ui =" not in source


def test_themed_builds_page_explicitly_composes_delete_action() -> None:
    source = Path(themed_builds_page.__file__).read_text(encoding="utf-8")

    assert "from ui.phase5_build_delete_support import attach_delete_build_action" in source
    assert "attach_delete_build_action(self)" in source
