from pathlib import Path


def test_coverage_page_uses_raid_review_tab_instead_of_uptime_analysis() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    assert 'self.tabs.addTab(self._raid_review_tab(), "RAID REVIEW")' in source
    assert '"UPTIME ANALYSIS"' not in source
    assert '"ENCOUNTER NEEDS"' in source


def test_raid_review_workspace_exposes_backend_binding_surfaces() -> None:
    source = Path("ui/coverage_page.py").read_text(encoding="utf-8")

    expected_surfaces = (
        "raid_review_priorities_card",
        "raid_review_working_card",
        "raid_review_role_focus_card",
        "raid_review_players_card",
        "raid_review_evidence_card",
    )
    for surface in expected_surfaces:
        assert f"self.{surface}" in source

    assert 'FoundryCard("Top Priorities"' in source
    assert 'FoundryCard("What Is Working"' in source
    assert 'FoundryCard("Role Focus"' in source
    assert 'FoundryCard("Player Review"' in source
    assert 'FoundryCard("Evidence & Unresolved"' in source
