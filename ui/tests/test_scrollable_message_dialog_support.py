from pathlib import Path


def test_long_message_support_is_installed_before_roster_import() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")
    assert source.index("install_scrollable_message_dialog_support()") < source.index(
        "install_roster_import_support()"
    )


def test_long_message_support_routes_information_warning_and_critical() -> None:
    source = Path("ui/scrollable_message_dialog_support.py").read_text(encoding="utf-8")
    assert '("information", "warning", "critical")' in source
    assert "QTextEdit()" in source
    assert "setReadOnly(True)" in source
    assert "setMinimumSize(520, 320)" in source
    assert "resize(760, 520)" in source
