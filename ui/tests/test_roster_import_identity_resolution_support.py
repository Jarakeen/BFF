from pathlib import Path


def test_roster_import_identity_matching_ignores_leading_at_sign():
    source = Path("ui/roster_import_identity_resolution_support.py").read_text(encoding="utf-8")

    assert '.lstrip("@")' in source
    assert "same_class" in source
    assert "len(same_class) == 1" in source
    assert "len(unique_names) == 1" in source
    assert "does not know which character owns it yet" in source


def test_roster_import_identity_support_is_installed_after_import_workflow():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_roster_import_identity_resolution_support()" in source
    assert source.index("install_roster_import_support()") < source.index(
        "install_roster_import_identity_resolution_support()"
    )
