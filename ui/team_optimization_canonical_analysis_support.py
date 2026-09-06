from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from engine.config import get_data_dir
from minmax.optimization_mode import policy_for_mode
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService
from services.team_optimization_canonical_analysis import (
    TeamOptimizationCanonicalAnalysis,
    TeamOptimizationCanonicalAnalysisService,
)
from services.team_optimization_static_comparison import (
    TeamOptimizationStaticComparison,
    TeamOptimizationStaticComparisonService,
)


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_UPDATE = None


def _active_table(page):
    if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
        return page.team_b_table
    return page.team_table


def _selected_builds_and_recruits(page, table=None):
    table = table or _active_table(page)
    builds = []
    recruits = 0
    for row in range(table.rowCount()):
        selector = table.cellWidget(row, 1)
        selection = selector.currentData() if isinstance(selector, QComboBox) else None
        if isinstance(selection, int) and 0 <= selection < len(page.roster.Members):
            builds.append(page.roster.Members[selection])
        elif isinstance(selection, str) and selection.startswith("recruitment:"):
            recruits += 1
    return tuple(builds), recruits


def _team_label(page) -> str:
    if hasattr(page, "team_tabs") and page.team_tabs.currentIndex() == 1:
        return "Team B"
    return "Team A"


def _loaded_team_name_for(page, label: str) -> str:
    attr = (
        "_optimization_loaded_team_name_b"
        if label == "Team B"
        else "_optimization_loaded_team_name_a"
    )
    return str(getattr(page, attr, "") or "").strip()


def _loaded_team_name(page) -> str:
    return _loaded_team_name_for(page, _team_label(page))


def _is_compare_mode(page) -> bool:
    try:
        return bool(policy_for_mode(page._current_mode()).uses_two_teams)
    except (AttributeError, IndexError, TypeError, ValueError):
        return False


def _format_analysis(page, result: TeamOptimizationCanonicalAnalysis) -> str:
    team = _team_label(page)
    name = _loaded_team_name(page)
    identity = f"{team} • {name}" if name else team
    clean = "✓ 0 capability-resolution gaps" if result.is_capability_clean else (
        f"⚠ {result.capability_gap_count} capability-resolution gap(s)"
    )
    return "\n".join(
        (
            identity,
            f"Saved canonical builds: {result.saved_build_count}",
            f"Recruit / open requirements: {result.recruit_count}",
            f"Resolved static support capabilities: {result.resolved_capability_count}",
            clean,
        )
    )


def _format_support(result: TeamOptimizationCanonicalAnalysis) -> str:
    if not result.capability_providers:
        return (
            "No static support capability is currently resolved from the selected saved builds.\n"
            "Recruitment requirements do not contribute capabilities until matched to canonical builds."
        )

    lines = []
    for effect_name, providers in result.capability_providers[:14]:
        lines.append(f"• {effect_name}: {', '.join(providers)}")
    remaining = len(result.capability_providers) - len(lines)
    if remaining > 0:
        lines.append(f"• +{remaining} more resolved static capability row(s)")
    lines.extend(
        (
            "",
            "Availability only. This does not assert encounter uptime or provider assignment.",
        )
    )
    return "\n".join(lines)


def _format_risks(result: TeamOptimizationCanonicalAnalysis) -> str:
    lines = []
    if result.recruit_count:
        lines.append(
            f"⚠ {result.recruit_count} recruit/open chair(s) are not canonical build contributors yet."
        )
    if result.capability_gap_count:
        lines.append(
            f"⚠ {result.capability_gap_count} saved-build capability gap(s) remain unresolved."
        )
    else:
        lines.append("✓ Selected saved builds have no capability-resolution gaps.")
    if result.conditional_source_count:
        lines.append(
            f"• {result.conditional_source_count} conditional source(s) require runtime conditions before uptime can be asserted."
        )
    if result.boundary_count:
        lines.append(
            f"• {result.boundary_count} explicit static/temporal boundary note(s) are preserved."
        )
    lines.append(
        "• Rotation timing, encounter uptime, sustain-through-rotation, and raid DPS are not ranked in this Phase 12.5 analysis."
    )
    return "\n".join(lines)


def _team_identity(page, label: str) -> str:
    name = _loaded_team_name_for(page, label)
    return f"{label} • {name}" if name else label


def _format_comparison_analysis(page, comparison: TeamOptimizationStaticComparison) -> str:
    a = comparison.team_a
    b = comparison.team_b
    return "\n".join(
        (
            _team_identity(page, "Team A"),
            f"{a.saved_build_count} saved build(s) • {a.recruit_count} recruit/open • {a.resolved_capability_count} static capabilities • {a.capability_gap_count} gap(s)",
            "",
            _team_identity(page, "Team B"),
            f"{b.saved_build_count} saved build(s) • {b.recruit_count} recruit/open • {b.resolved_capability_count} static capabilities • {b.capability_gap_count} gap(s)",
            "",
            f"Shared static capabilities: {len(comparison.shared_capabilities)}",
        )
    )


def _format_capability_list(title: str, values: tuple[str, ...]) -> list[str]:
    lines = [title]
    if not values:
        lines.append("• None")
        return lines
    for value in values[:10]:
        lines.append(f"• {value}")
    if len(values) > 10:
        lines.append(f"• +{len(values) - 10} more")
    return lines


def _format_comparison_support(comparison: TeamOptimizationStaticComparison) -> str:
    lines = []
    lines.extend(_format_capability_list("TEAM A ONLY", comparison.team_a_only_capabilities))
    lines.append("")
    lines.extend(_format_capability_list("TEAM B ONLY", comparison.team_b_only_capabilities))
    lines.extend(
        (
            "",
            f"Redundant capability rows: Team A {comparison.team_a_redundancy_count} • Team B {comparison.team_b_redundancy_count}",
            "Availability only. No encounter-aware winner is declared here.",
        )
    )
    return "\n".join(lines)


def _format_comparison_risks(comparison: TeamOptimizationStaticComparison) -> str:
    a = comparison.team_a
    b = comparison.team_b
    lines = [
        f"Team A: {a.recruit_count} recruit/open chair(s), {a.capability_gap_count} capability gap(s), {a.conditional_source_count} conditional source(s), {a.boundary_count} boundary note(s).",
        f"Team B: {b.recruit_count} recruit/open chair(s), {b.capability_gap_count} capability gap(s), {b.conditional_source_count} conditional source(s), {b.boundary_count} boundary note(s).",
        "No encounter-aware winner is declared. Static capability breadth is not the same thing as raid performance.",
        "Rotation timing, encounter uptime, sustain-through-rotation, and raid DPS remain outside this Phase 12.5 comparison.",
    ]
    return "\n".join(lines)


def _replace_placeholder_surfaces(page) -> None:
    page.analysis_card.title_label.setText("Canonical Team Analysis")
    page.support_card.title_label.setText("Static Support Capabilities")
    page.risks_card.title_label.setText("Evidence Boundaries & Risks")

    for name in ("gear_card", "skill_card", "notes_card"):
        card = getattr(page, name, None)
        if card is not None:
            card.hide()
            card.setMaximumHeight(0)


def _analyze_table(page, table) -> TeamOptimizationCanonicalAnalysis:
    builds, recruits = _selected_builds_and_recruits(page, table)
    return page._optimization_canonical_analysis_service.analyze(
        builds,
        recruit_count=recruits,
    )


def _refresh_canonical_analysis(page) -> None:
    service = getattr(page, "_optimization_canonical_analysis_service", None)
    if service is None or not hasattr(page, "analysis_summary"):
        return
    try:
        if _is_compare_mode(page):
            team_a = _analyze_table(page, page.team_table)
            team_b = _analyze_table(page, page.team_b_table)
            comparison = page._optimization_static_comparison_service.compare(team_a, team_b)
            page._optimization_current_canonical_comparison = comparison
            page._optimization_current_canonical_analysis = None
            page.analysis_card.title_label.setText("Canonical Team Comparison")
            page.support_card.title_label.setText("Static Capability Differences")
            page.risks_card.title_label.setText("Comparison Boundaries & Risks")
            page.analysis_summary.setText(_format_comparison_analysis(page, comparison))
            page.support_text.setText(_format_comparison_support(comparison))
            page.risks_text.setText(_format_comparison_risks(comparison))
            return

        builds, recruits = _selected_builds_and_recruits(page)
        result = service.analyze(builds, recruit_count=recruits)
    except (OSError, ValueError) as exc:
        page.analysis_summary.setText("Canonical capability analysis unavailable.")
        page.support_text.setText("No capability summary produced.")
        page.risks_text.setText(f"⚠ Canonical capability analysis failed: {exc}")
        return

    page._optimization_current_canonical_comparison = None
    page._optimization_current_canonical_analysis = result
    page.analysis_card.title_label.setText("Canonical Team Analysis")
    page.support_card.title_label.setText("Static Support Capabilities")
    page.risks_card.title_label.setText("Evidence Boundaries & Risks")
    page.analysis_summary.setText(_format_analysis(page, result))
    page.support_text.setText(_format_support(result))
    page.risks_text.setText(_format_risks(result))


def _update_with_canonical_analysis(self) -> None:
    assert _ORIGINAL_UPDATE is not None
    _ORIGINAL_UPDATE(self)
    _refresh_canonical_analysis(self)


def _init_with_canonical_analysis(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)
    data_dir = get_data_dir()
    builds = BuildService(data_dir / "builds.json")
    capability = SavedBuildCapabilityService(builds, data_dir / "eso.db")
    self._optimization_canonical_analysis_service = TeamOptimizationCanonicalAnalysisService(
        capability
    )
    self._optimization_static_comparison_service = TeamOptimizationStaticComparisonService()
    self._optimization_current_canonical_analysis = None
    self._optimization_current_canonical_comparison = None
    _replace_placeholder_surfaces(self)
    if hasattr(self, "team_tabs"):
        self.team_tabs.currentChanged.connect(lambda *_: _refresh_canonical_analysis(self))
    if hasattr(self, "mode_tabs"):
        self.mode_tabs.currentChanged.connect(lambda *_: _refresh_canonical_analysis(self))
    _refresh_canonical_analysis(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_UPDATE
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    _ORIGINAL_UPDATE = OptimizationPage._update_team_analysis
    OptimizationPage._update_team_analysis = _update_with_canonical_analysis
    _ORIGINAL_INIT = OptimizationPage.__init__
    OptimizationPage.__init__ = _init_with_canonical_analysis
    _INSTALLED = True
