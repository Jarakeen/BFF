from pathlib import Path

from services.team_optimization_canonical_analysis import TeamOptimizationCanonicalAnalysis
from services.team_optimization_static_comparison import (
    TeamOptimizationStaticComparisonService,
)


def _analysis(
    providers=(),
    *,
    saved=0,
    recruits=0,
    gaps=0,
    conditional=0,
    boundaries=0,
):
    return TeamOptimizationCanonicalAnalysis(
        saved_build_count=saved,
        recruit_count=recruits,
        build_summaries=(),
        capability_providers=tuple(providers),
        capability_gap_count=gaps,
        conditional_source_count=conditional,
        boundary_count=boundaries,
    )


def test_static_comparison_reports_shared_and_unique_capabilities() -> None:
    team_a = _analysis(
        (
            ("Major Resolve", ("Tank A",)),
            ("Minor Brittle", ("Healer A",)),
            ("Major Vulnerability", ("DD A",)),
        )
    )
    team_b = _analysis(
        (
            ("Major Resolve", ("Tank B",)),
            ("Major Slayer", ("Healer B",)),
        )
    )

    result = TeamOptimizationStaticComparisonService().compare(team_a, team_b)

    assert result.shared_capabilities == ("Major Resolve",)
    assert result.team_a_only_capabilities == ("Major Vulnerability", "Minor Brittle")
    assert result.team_b_only_capabilities == ("Major Slayer",)


def test_static_comparison_counts_redundant_provider_rows_without_ranking_them() -> None:
    team_a = _analysis(
        (
            ("Major Resolve", ("Tank A", "Healer A")),
            ("Minor Berserk", ("Healer A",)),
        )
    )
    team_b = _analysis(
        (
            ("Major Resolve", ("Tank B",)),
            ("Minor Berserk", ("Healer B", "DD B", "Tank B")),
        )
    )

    result = TeamOptimizationStaticComparisonService().compare(team_a, team_b)

    assert result.team_a_redundant_capabilities == (("Major Resolve", 2),)
    assert result.team_b_redundant_capabilities == (("Minor Berserk", 3),)
    assert result.team_a_redundancy_count == 1
    assert result.team_b_redundancy_count == 1


def test_compare_mode_ui_analyzes_both_team_tables_not_only_active_tab() -> None:
    source = Path("ui/team_optimization_canonical_analysis_support.py").read_text(
        encoding="utf-8"
    )

    assert "team_a = _analyze_table(page, page.team_table)" in source
    assert "team_b = _analyze_table(page, page.team_b_table)" in source
    assert "page._optimization_static_comparison_service.compare(team_a, team_b)" in source
    assert 'page.analysis_card.title_label.setText("Canonical Team Comparison")' in source
    assert 'page.support_card.title_label.setText("Static Capability Differences")' in source


def test_compare_mode_preserves_both_named_team_identities() -> None:
    source = Path("ui/team_optimization_canonical_analysis_support.py").read_text(
        encoding="utf-8"
    )

    assert "_loaded_team_name_for(page, label)" in source
    assert '_team_identity(page, "Team A")' in source
    assert '_team_identity(page, "Team B")' in source
    assert '"_optimization_loaded_team_name_a"' in source
    assert '"_optimization_loaded_team_name_b"' in source


def test_static_comparison_refuses_to_invent_encounter_winner_or_dps() -> None:
    source = Path("ui/team_optimization_canonical_analysis_support.py").read_text(
        encoding="utf-8"
    )

    assert "No encounter-aware winner is declared here." in source
    assert "No encounter-aware winner is declared. Static capability breadth is not the same thing as raid performance." in source
    assert "Rotation timing, encounter uptime, sustain-through-rotation, and raid DPS remain outside" in source
    assert "winner =" not in source.casefold()
