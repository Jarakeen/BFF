from __future__ import annotations

import inspect


def test_scribing_editor_compat_accepts_selected_build():
    from ui.components.searchable_build_selectors import install as install_searchable_selectors
    from ui.scribing_support import install as install_scribing_support
    from ui.scribing_editor_compat import install as install_scribing_editor_compat

    install_searchable_selectors()
    install_scribing_support()
    install_scribing_editor_compat()

    from ui.builds_page import BuildsPage

    signature = inspect.signature(BuildsPage._editor)
    assert "build" in signature.parameters
    assert signature.parameters["build"].default is None
