from __future__ import annotations

from pathlib import Path

from ui import icon_consistency


def test_legacy_tool_and_cog_symbols_are_always_stripped() -> None:
    assert "⚒" in icon_consistency._ALWAYS_STRIP
    assert "⚙" in icon_consistency._ALWAYS_STRIP


def test_settings_uses_real_svg_icon_mapping() -> None:
    source = Path(icon_consistency.__file__).read_text(encoding="utf-8")

    for icon_name in (
        "settings.svg",
        "gears.svg",
        "archive.svg",
        "broadcast.svg",
        "download.svg",
        "square-library.svg",
        "refresh.svg",
    ):
        assert icon_name in source

    assert '"Backup Data"' in source
    assert '"Export Settings"' in source
    assert '"Import Settings"' in source
    assert '"Reset to Defaults"' in source


def test_button_icon_filter_guards_reentrant_polish_events() -> None:
    source = Path(icon_consistency.__file__).read_text(encoding="utf-8")

    assert "self._processing: set[int] = set()" in source
    assert "if key in self._processing:" in source
    assert "self._processing.add(key)" in source
    assert "self._processing.discard(key)" in source
