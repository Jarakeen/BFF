from pathlib import Path
from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.team_optimization_canonical_analysis import (
    TeamOptimizationCanonicalAnalysisService,
)


class _FakeCapabilityService:
    def __init__(self, audits):
        self.audits = audits

    def audit_build(self, build):
        return self.audits[build.BuildName]


def _audit(*effects, gaps=(), conditional=(), boundaries=()):
    return SimpleNamespace(
        resolved_effects=tuple(SimpleNamespace(name=name) for name in effects),
        capability_resolution_gaps=tuple(gaps),
        conditional_sources=tuple(conditional),
        boundaries=tuple(boundaries),
    )


def test_canonical_team_analysis_merges_real_saved_build_capabilities() -> None:
    magrat = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    susan = PlayerBuild(Name="Susan", BuildName="Necro Tank")
    service = TeamOptimizationCanonicalAnalysisService(
        _FakeCapabilityService(
            {
                "DF Healer": _audit("Minor Berserk", "Major Resolve"),
                "Necro Tank": _audit("Major Resolve", "Major Vulnerability"),
            }
        )
    )

    result = service.analyze((magrat, susan), recruit_count=1)

    assert result.saved_build_count == 2
    assert result.recruit_count == 1
    assert result.resolved_capability_count == 3
    assert dict(result.capability_providers) == {
        "Major Resolve": ("Magrat", "Susan"),
        "Major Vulnerability": ("Susan",),
        "Minor Berserk": ("Magrat",),
    }
    assert result.is_capability_clean is True


def test_canonical_team_analysis_keeps_gaps_conditions_and_boundaries_explicit() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    service = TeamOptimizationCanonicalAnalysisService(
        _FakeCapabilityService(
            {
                "DF Healer": _audit(
                    "Minor Berserk",
                    gaps=("unknown skill mapping",),
                    conditional=("Master Architect", "Potion"),
                    boundaries=("Potion selected; uptime unresolved",),
                )
            }
        )
    )

    result = service.analyze((build,))

    assert result.capability_gap_count == 1
    assert result.conditional_source_count == 2
    assert result.boundary_count == 1
    assert result.is_capability_clean is False
    assert result.build_summaries[0].capability_gaps == ("unknown skill mapping",)


def test_optimization_ui_uses_canonical_capability_service_without_claiming_dps() -> None:
    source = Path("ui/team_optimization_canonical_analysis_support.py").read_text(
        encoding="utf-8"
    )

    assert "SavedBuildCapabilityService" in source
    assert "TeamOptimizationCanonicalAnalysisService" in source
    assert "service.analyze(builds, recruit_count=recruits)" in source
    assert "Resolved static support capabilities" in source
    assert "Availability only. This does not assert encounter uptime or provider assignment." in source
    assert "Rotation timing, encounter uptime, sustain-through-rotation, and raid DPS are not ranked" in source


def test_optimization_analysis_only_counts_selected_saved_builds_and_recruits() -> None:
    source = Path("ui/team_optimization_canonical_analysis_support.py").read_text(
        encoding="utf-8"
    )

    assert "selection = selector.currentData()" in source
    assert "page.roster.Members[selection]" in source
    assert 'selection.startswith("recruitment:")' in source
    assert "recruits += 1" in source


def test_canonical_optimization_analysis_replaces_placeholder_surfaces() -> None:
    source = Path("ui/team_optimization_canonical_analysis_support.py").read_text(
        encoding="utf-8"
    )

    assert 'page.analysis_card.title_label.setText("Canonical Team Analysis")' in source
    assert 'page.support_card.title_label.setText("Static Support Capabilities")' in source
    assert 'page.risks_card.title_label.setText("Evidence Boundaries & Risks")' in source
    assert 'for name in ("gear_card", "skill_card", "notes_card")' in source
    assert "card.hide()" in source
    assert "card.setMaximumHeight(0)" in source


def test_canonical_optimization_analysis_is_installed_after_roster_load_refocus() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    role_cleanup = installer.index("install_role_cleanup()")
    canonical = installer.index("install_team_optimization_canonical_analysis()")
    assert role_cleanup < canonical
