from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.performance_model import AbilityBreakdown, AbilityUptime
from ui.performance_dashboard_healer_support import (
    _healer_readout_lines,
    _response_value,
    _support_gap_value,
)


def _snapshot(**overrides):
    values = {
        "HealerCritRatePercent": 41.5,
        "HealerCriticalEvents": 415,
        "HealerHealingEvents": 1000,
        "ObservedHotUptimes": [
            AbilityUptime(Name="Radiating Regeneration", UptimeSeconds=80, UptimePercent=80.0),
            AbilityUptime(Name="Illustrious Healing", UptimeSeconds=62, UptimePercent=62.0),
        ],
        "HealerResponseSelectedEvents": 12,
        "HealerPrecoveredEvents": 7,
        "HealerRespondedEvents": 9,
        "HealerUnansweredEvents": 1,
        "HealerMedianResponseMs": 430.0,
        "HealerLargestResponseMs": 1180.0,
        "HealerSupportCastCount": 140,
        "HealerSupportGapCount": 3,
        "HealerLargestSupportGapSeconds": 5.2,
        "HealerSupportGapExcessSeconds": 4.1,
        "HealerSupportGapThresholdSeconds": 3.0,
        "TopAbilities": [
            AbilityBreakdown(Name="Illustrious Healing", Total=2_000_000, Percent=24.2),
        ],
        "DebuffUptimes": [
            AbilityUptime(Name="Minor Vulnerability", UptimeSeconds=70, UptimePercent=70.0),
        ],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_healer_readout_combines_coverage_response_cadence_and_contribution() -> None:
    lines = _healer_readout_lines(_snapshot())

    assert "Healing crit: 41.5% of observed healing events (415/1,000)." in lines
    assert any("62.0% (Illustrious Healing) to 80.0% (Radiating Regeneration)" in line for line in lines)
    assert any("12 upper-quartile raid damage events" in line and "median observed response 430 ms" in line for line in lines)
    assert any("140 meaningful casts" in line and "largest 5.2s" in line for line in lines)
    assert "Top healing source: Illustrious Healing at 24.2% of total healing." in lines
    assert any("Minor Vulnerability" in line for line in lines)
    assert not any("mistake" in line.casefold() or "failed" in line.casefold() for line in lines)


def test_healer_readout_has_empty_evidence_state() -> None:
    lines = _healer_readout_lines(
        _snapshot(
            HealerCritRatePercent=None,
            HealerCriticalEvents=0,
            HealerHealingEvents=0,
            ObservedHotUptimes=[],
            HealerResponseSelectedEvents=0,
            HealerPrecoveredEvents=0,
            HealerRespondedEvents=0,
            HealerUnansweredEvents=0,
            HealerMedianResponseMs=None,
            HealerLargestResponseMs=None,
            HealerSupportCastCount=0,
            HealerSupportGapCount=0,
            HealerLargestSupportGapSeconds=None,
            TopAbilities=[],
            DebuffUptimes=[],
        )
    )
    assert lines == ["No healer diagnostic evidence is available for this snapshot yet."]


def test_healer_kpi_text_helpers_are_conservative() -> None:
    assert _response_value(_snapshot()) == "9/12 • 430 ms"
    assert _support_gap_value(_snapshot()) == "3 • max 5.2s"
    assert _response_value(_snapshot(HealerResponseSelectedEvents=0)) == "No sample"
    assert _support_gap_value(_snapshot(HealerSupportGapCount=0)) == "No long gaps"


def test_healer_ui_is_role_gated_and_describes_evidence_boundaries() -> None:
    source = Path("ui/performance_dashboard_healer_support.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Healer Readout")' in source
    assert '"Observed HoT Coverage"' in source
    assert 'casefold() == "healer"' in source
    assert '"Heal Crit"' in source
    assert '"Healing Response"' in source
    assert '"Support Cadence"' in source
    assert "HPS is not graded as a universal healer score" in source
    assert "they do not prove assignment success or failure" in source


def test_healer_stack_is_installed_before_main_window_construction() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    assert "install_performance_healer_analysis_support()" in source
    assert "install_performance_dashboard_healer_support()" in source
    assert source.index("install_performance_healer_analysis_support()") < source.index(
        "from ui.main_window import MainWindow"
    )
