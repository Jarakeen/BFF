from pathlib import Path

from ui import build_editor_inline_compat


def test_build_editor_uses_tab_instead_of_native_dialog() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    # Documentation may mention the former dialog implementation. The safety
    # invariant is that the active Build Editor never constructs or executes a
    # native dialog and remains on the existing dark application surface.
    assert "QDialog(" not in source
    assert "dialog.exec(" not in source
    assert 'DARK_SURFACE = "#0C171B"' in source
    assert "QTabWidget" in source
    assert 'tabs.addTab(self.splitter, "Builds")' in source
    assert 'tabs.addTab(host, f"Edit: {name}")' in source
    assert "tabs.setCurrentWidget(host)" in source
    assert "self.splitter.hide()" not in source
    assert "host.show()" not in source


def test_tabbed_editor_remembers_original_build_index() -> None:
    source = Path(build_editor_inline_compat.__file__).read_text(encoding="utf-8")

    assert "self._build_editor_index = index" in source
    assert "original = self.roster.Members[index]" in source
    assert "self.roster.Members[index] = updated" in source


def test_inline_editor_is_installed_after_other_build_extensions() -> None:
    app_source = (Path(build_editor_inline_compat.__file__).parent.parent / "app.py").read_text(
        encoding="utf-8"
    )

    assert "install_inline_build_editor()" in app_source
    assert app_source.index("install_inline_build_editor()") > app_source.index(
        "install_phase5_potion_picker_support()"
    )
