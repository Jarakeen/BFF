from pathlib import Path

from ui import foundry_theme


def test_foundry_theme_sets_native_dark_window_palette() -> None:
    source = Path(foundry_theme.__file__).read_text(encoding="utf-8")

    assert 'QPalette.ColorRole.Window, QColor("#0d0f0e")' in source
    assert 'QPalette.ColorRole.Base, QColor("#111411")' in source
    assert "app.setPalette(palette)" in source
    assert source.index("app.setPalette(palette)") < source.index("app.setStyleSheet(FOUNDry_STYLESHEET)")
