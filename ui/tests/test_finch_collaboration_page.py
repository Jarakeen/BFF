from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_finch_collaboration_page_is_explicit_read_only_overview() -> None:
    source = _source("ui/finch_collaboration_page.py")

    assert 'QPushButton("Refresh Finch")' in source
    assert 'QPushButton("Open Workspace")' in source
    assert "load_finch_collaboration_overview" in source
    assert "Publishing and Copy to Local" in source
    assert "owning workspaces." in source
    assert "publish_" not in source
    assert "import_shared_" not in source


def test_finch_collaboration_does_not_fetch_during_construction() -> None:
    source = _source("ui/finch_collaboration_page.py")
    constructor = source[
        source.index("    def __init__")
        : source.index("    def _build_ui")
    ]

    assert "refresh_from_finch()" not in constructor
    assert "_FINCH_COLLAB_EXECUTOR.submit" not in constructor


def test_finch_collaboration_route_is_registered_in_phase14_team_navigation() -> None:
    sidebar = _source("ui/components/foundry_sidebar.py")
    support = _source("ui/raid_engine_dashboard_support.py")

    assert '("Finch Collaboration", "finch_collaboration")' in sidebar
    assert '("Finch Collaboration", "finch_collaboration")' in support
    assert 'from ui.finch_collaboration_page import FinchCollaborationPage' in support
    assert '_register_page(window, "finch_collaboration", finch_collaboration)' in support
    assert "finch_collaboration.pageRequested.connect(window.show_page)" in support
