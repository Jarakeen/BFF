from pathlib import Path

from ui import foundry_theme


def test_foundry_theme_sets_native_dark_window_palette() -> None:
    source = Path(foundry_theme.__file__).read_text(encoding="utf-8")

    assert 'SAFE_DIALOG_BACKGROUND = "#0C171B"' in source
    assert "QPalette.ColorRole.Window, QColor(SAFE_DIALOG_BACKGROUND)" in source
    assert 'QPalette.ColorRole.Base, QColor("#111411")' in source
    assert "app.setPalette(palette)" in source
    assert source.index("app.setPalette(palette)") < source.index("app.setStyleSheet(FOUNDry_STYLESHEET)")


def test_foundry_theme_forces_dark_dialog_prepaint() -> None:
    source = Path(foundry_theme.__file__).read_text(encoding="utf-8")

    assert "class _DarkDialogPrepaintFilter(QObject):" in source
    assert "QEvent.Type.Polish" in source
    assert "QEvent.Type.Show" in source
    assert "WA_OpaquePaintEvent" in source
    assert "setAutoFillBackground(True)" in source
    assert "QAbstractScrollArea" in source
    assert "app.installEventFilter(app._foundry_dark_dialog_filter)" in source
