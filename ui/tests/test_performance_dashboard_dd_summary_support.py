from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.performance_model import AbilityBreakdown, AbilityUptime
from ui.performance_dashboard_dd_summary_support import _dd_readout_lines


def _snapshot(**overrides):
    values = {
        "CritRatePercent": 42.7,
        "CriticalDamageEvents": 427,
        "DamageHitEvents": 1000,
        "WeavePairingPercent": 92.4,
        "WeavePairedSkillCasts": 121,
        "WeaveSkillCasts": 131,
        "WeaveUnpairedSkillCasts": 10,
        "WeaveMedianPairDelayMs": 137.0,
        "ObservedDotUptimes": [
            AbilityUptime(Name="Burning Embers", UptimeSeconds=80.0, UptimePercent=80.0),
            AbilityUptime(Name="Trap", UptimeSeconds=63.2, UptimePercent=63.2),
        ],
        "TopAbilities": [
            AbilityBreakdown(Name="Whip", Total=2_000_000, Percent=23.4),
        ],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_dd_readout_combines_actionable_observations_without_grading() -> None:
    lines = _dd_readout_lines(_snapshot())

    assert "Crit: 42.7% of observed damage events (427/1,000)." in lines
    assert any("LA pairing: 121/131" in line and "10 unpaired" in line for line in lines)
    assert any("63.2% (Trap) to 80.0% (Burning Embers)" in line for line in lines)
    assert "Top damage source: Whip at 23.4% of total damage." in lines
    assert "Review first: 10 eligible skill casts had no observed preceding Light Attack." in lines
    assert not any("good" in line.casefold() or "bad" in line.casefold() for line in lines)


def test_dd_readout_does_not_invent_a_problem_when_pairing_has_no_misses() -> None:
    lines = _dd_readout_lines(
        _snapshot(
            WeavePairingPercent=100.0,
            WeavePairedSkillCasts=40,
            WeaveSkillCasts=40,
            WeaveUnpairedSkillCasts=0,
        )
    )

    assert "No unpaired eligible skill casts were observed in the LA-pairing window." in lines
    assert not any(line.startswith("Review first:") for line in lines)


def test_dd_readout_has_an_explicit_empty_evidence_state() -> None:
    lines = _dd_readout_lines(
        _snapshot(
            CritRatePercent=None,
            CriticalDamageEvents=0,
            DamageHitEvents=0,
            WeavePairingPercent=None,
            WeavePairedSkillCasts=0,
            WeaveSkillCasts=0,
            WeaveUnpairedSkillCasts=0,
            WeaveMedianPairDelayMs=None,
            ObservedDotUptimes=[],
            TopAbilities=[],
        )
    )

    assert lines == ["No DD diagnostic evidence is available for this snapshot yet."]


def test_dd_stack_wires_weave_and_summary_from_existing_startup_hooks() -> None:
    service_dot = Path("services/performance_dd_dot_support.py").read_text(encoding="utf-8")
    ui_dot = Path("ui/performance_dashboard_dd_dot_support.py").read_text(encoding="utf-8")
    ui_weave = Path("ui/performance_dashboard_dd_weave_support.py").read_text(encoding="utf-8")
    summary = Path("ui/performance_dashboard_dd_summary_support.py").read_text(encoding="utf-8")

    assert "performance_dd_weave_support" in service_dot
    assert "performance_dashboard_dd_weave_support" in ui_dot
    assert "performance_dashboard_dd_summary_support" in ui_weave
    assert 'FoundryCard("DD Readout")' in summary
    assert "not graded against build-specific targets" in summary
