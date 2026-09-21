from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_coverage_page_exposes_explicit_finch_actions() -> None:
    source = _source("ui/coverage_page.py")

    assert 'QPushButton("Publish Coverage")' in source
    assert 'QPushButton("Get Shared Coverage")' in source
    assert "publish_coverage_to_finch" in source
    assert "list_shared_coverage_from_finch" in source
    assert "This is a read-only Finch snapshot. Local Coverage was not changed." in source


def test_coverage_refresh_does_not_publish_or_fetch_finch() -> None:
    source = _source("ui/coverage_page.py")
    refresh = source[
        source.index("    def refresh(self):")
        : source.index("    def _apply_coverage_filters")
        if "    def _apply_coverage_filters" in source[source.index("    def refresh(self):"):]
        else len(source)
    ]

    assert "publish_coverage_to_finch" not in refresh
    assert "list_shared_coverage_from_finch" not in refresh
    assert "_FINCH_COVERAGE_EXECUTOR" not in refresh


def test_shared_coverage_view_is_read_only() -> None:
    source = _source("ui/coverage_page.py")
    shared = source[
        source.index("    def _get_shared_coverage_from_finch")
        : source.index("    @staticmethod\n    def _context_field")
    ]

    assert "RaidPlanRepository.save" not in shared
    assert "set_human_ready" not in shared
    assert "local state unchanged" in shared


def test_coverage_publish_requires_saved_raid_plan_scope() -> None:
    source = _source("ui/coverage_page.py")

    assert 'data.startswith("raid_plan:")' in source
    assert "Select a saved Raid Plan before publishing Coverage." in source
