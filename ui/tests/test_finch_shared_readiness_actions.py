from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readiness_page_exposes_explicit_finch_actions() -> None:
    source = _source("ui/city_raid_readiness_page.py")

    assert 'QPushButton("Publish Readiness")' in source
    assert 'QPushButton("Get Shared Readiness")' in source
    assert "publish_readiness_to_finch" in source
    assert "list_shared_readiness_from_finch" in source
    assert "This is a read-only Finch snapshot. Local Readiness was not changed." in source


def test_readiness_refresh_does_not_publish_or_fetch_finch() -> None:
    source = _source("ui/city_raid_readiness_page.py")
    refresh = source[
        source.index("    def refresh_plans(self) -> None:")
        : source.index("    def _load_selected_plan")
    ]

    assert "publish_readiness_to_finch" not in refresh
    assert "list_shared_readiness_from_finch" not in refresh
    assert "_FINCH_READINESS_EXECUTOR" not in refresh


def test_shared_readiness_view_does_not_write_local_human_ready_state() -> None:
    source = _source("ui/city_raid_readiness_page.py")
    shared = source[
        source.index("    def _get_shared_readiness_from_finch")
        : source.index("    def refresh_plans")
    ]

    assert "set_human_ready" not in shared
    assert "RaidPlanRepository.save" not in shared
    assert "local state unchanged" in shared


def test_shared_readiness_picker_shows_publisher_and_utc_time() -> None:
    source = _source("ui/city_raid_readiness_page.py")

    assert "row.published_by" in source
    assert "format_shared_timestamp(row.updated_at)" in source


def test_readiness_refreshes_current_plan_evidence_when_page_becomes_visible() -> None:
    source = Path("ui/city_raid_readiness_page.py").read_text(encoding="utf-8")

    assert "def showEvent(self, event) -> None:" in source
    assert "self.refresh_plans()" in source
    assert "stale !GAP matrix" in source
