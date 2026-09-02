from pathlib import Path

from ui import build_editor_inline_compat


def test_build_editor_uses_existing_page_instead_of_native_dialog() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    assert "QDialog" not in source
    assert 'DARK_SURFACE = "#0C171B"' in source
    assert "self.workspace_layout.addWidget(host, 1)" in source
    assert "self.splitter.hide()" in source
    assert "host.show()" in source


def test_inline_editor_is_installed_after_other_build_extensions() -> None:
    app_source = (Path(build_editor_inline_compat.__file__).parent.parent / "app.py").read_text(
        encoding="utf-8"
    )

    assert "install_inline_build_editor()" in app_source
    assert app_source.index("install_inline_build_editor()") > app_source.index(
        "install_phase5_potion_picker_support()"
    )
