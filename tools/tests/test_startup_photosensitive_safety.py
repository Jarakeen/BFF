from pathlib import Path


def test_startup_splash_contract_is_static_and_motion_free() -> None:
    source = Path("ui/startup_splash.py").read_text(encoding="utf-8")

    assert "completely static, motion-free startup screen" in source
    assert "Neither version animates, blinks, fades" in source
    assert "moving progress indicator" in source
    assert "QTimer" not in source
    assert "QPropertyAnimation" not in source
    assert "QMovie" not in source


def test_pyinstaller_boot_splash_closes_only_after_qt_splash_is_visible() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    main = source.split("def main() -> int:", 1)[1]

    create_index = main.index("splash = create_startup_splash()")
    show_index = main.index("splash.show()")
    process_index = main.index("app.processEvents()")
    close_index = main.index("_close_pyinstaller_boot_splash()")

    assert create_index < show_index < process_index < close_index


def test_startup_safety_rationale_stays_explicit() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert "prevents a bright/blank handoff gap during" in source
    assert "photosensitive users" in source
