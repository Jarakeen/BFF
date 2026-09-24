from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_finch_collaboration_page_is_explicit_read_only_overview() -> None:
    source = _source("ui/finch_collaboration_page.py")

    assert 'QPushButton("Refresh Finch")' in source
    assert 'QPushButton("Open Workspace")' in source
    assert "load_finch_collaboration_overview" in source
    assert "Publish and Copy to Local" in source
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


def test_finch_collaboration_page_exposes_attention_filters_and_counts() -> None:
    source = _source("ui/finch_collaboration_page.py")

    for label in (
        "All Shared",
        "Changed Since Copy",
        "Not Copied",
        "Readiness Gaps",
        "Coverage Gaps",
    ):
        assert label in source

    assert 'self.changed_label = QLabel("Changed since copy: 0")' in source
    assert 'self.not_copied_label = QLabel("Not copied: 0")' in source
    assert 'self.readiness_gap_label = QLabel("Readiness gaps: 0")' in source
    assert 'self.coverage_gap_label = QLabel("Coverage gaps: 0")' in source
    assert "tag in row.attention_tags" in source


def test_finch_collaboration_open_workspace_emits_structured_context() -> None:
    page = _source("ui/finch_collaboration_page.py")
    support = _source("ui/raid_engine_dashboard_support.py")

    assert "workspaceRequested = Signal(str, str)" in page
    assert "self.workspaceRequested.emit(row.route, row.context_key)" in page
    assert "def _open_finch_collaboration_workspace(" in support
    assert 'route == "raid_plans" and context_key' in support
    assert 'route == "readiness" and context_key' in support
    assert 'route == "console:7" and context_key' in support
    assert "finch_collaboration.workspaceRequested.connect(" in support


def test_finch_collaboration_handoff_falls_back_without_local_context() -> None:
    support = _source("ui/raid_engine_dashboard_support.py")
    handoff = support[
        support.index("def _open_finch_collaboration_workspace(")
        : support.index("def _open_exact_build")
    ]

    assert "window.show_page(route)" in handoff
    assert "context_key" in handoff
    assert "plan_repository" in handoff
