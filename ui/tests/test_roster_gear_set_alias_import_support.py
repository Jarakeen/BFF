from __future__ import annotations

from pathlib import Path


def test_alias_import_support_wraps_slot_and_apply_paths() -> None:
    source = Path("ui/roster_gear_set_alias_import_support.py").read_text(encoding="utf-8")
    assert "roster_import_workflow._slot_payload = _slot_payload_with_aliases" in source
    assert "roster_import_workflow.apply_roster_import = apply_roster_import_with_set_aliases" in source
    assert "backfill_saved_build_gear_aliases" in source
    assert "create_backup=True" in source


def test_alias_support_installs_after_identity_resolution_and_before_preview() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")
    identity = source.index("install_roster_import_identity_resolution_support()")
    aliases = source.index("install_roster_gear_set_alias_import_support()")
    preview = source.index("install_roster_import_match_preview_support()")
    assert identity < aliases < preview
