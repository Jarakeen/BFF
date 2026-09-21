from pathlib import Path


def test_roster_page_exposes_explicit_nonblocking_finch_sync_action() -> None:
    source = Path("ui/roster_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Sync Finch")' in source
    assert "sync_finch_gear_needs" in source
    assert "ThreadPoolExecutor" in source
    assert "_finch_sync_timer" in source
    assert "self.refresh()" in source


def test_finch_sync_is_not_bound_to_roster_refresh() -> None:
    source = Path("ui/roster_page.py").read_text(encoding="utf-8")

    refresh_start = source.index("    def refresh(self):")
    filtered_start = source.index("    def _filtered_members", refresh_start)
    refresh_source = source[refresh_start:filtered_start]

    assert "sync_finch_gear_needs" not in refresh_source
    assert "pending_gear_needs" not in refresh_source
