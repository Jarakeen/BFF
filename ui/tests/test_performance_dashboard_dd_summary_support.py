from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.performance_model import AbilityBreakdown, AbilityUptime
from ui.performance_dashboard_dd_summary_support import (
    _dd_readout_lines,
    _enforce_dd_card_visibility,
)


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
        "ObservedActionGapCount": 3,
        "ObservedLargestActionGapSeconds": 6.1,
        "ObservedActionGapExcessSeconds": 8.6,
        "ActivityGapThresholdSeconds": 2.5,
        "ActionGapRaidQuietCount": 1,
        "ActionGapRaidActiveCount": 1,
        "ActionGapUnknownCount": 1,
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


class _VisibleCard:
    def __init__(self):
        self.visible = None

    def setVisible(self, visible: bool) -> None:
        self.visible = bool(visible)


def test_final_dd_card_visibility_hides_support_cards_and_keeps_dot_card() -> None:
    dashboard = SimpleNamespace(
        buff_card=_VisibleCard(),
        debuff_card=_VisibleCard(),
        raid_debuff_card=_VisibleCard(),
        support_effects_card=_VisibleCard(),
        dot_card=_VisibleCard(),
    )

    _enforce_dd_card_visibility(dashboard, True)

    assert dashboard.buff_card.visible is False
    assert dashboard.debuff_card.visible is False
    assert dashboard.raid_debuff_card.visible is False
    assert dashboard.support_effects_card.visible is False
    assert dashboard.dot_card.visible is True

    _enforce_dd_card_visibility(dashboard, False)

    assert dashboard.buff_card.visible is True
    assert dashboard.debuff_card.visible is True
    assert dashboard.raid_debuff_card.visible is True
    assert dashboard.support_effects_card.visible is True
    assert dashboard.dot_card.visible is False


def test_dd_readout_combines_actionable_observations_without_grading() -> None:
    lines = _dd_readout_lines(_snapshot())

    assert "Crit: 42.7% of observed damage events (427/1,000)." in lines
    assert any("LA pairing: 121/131" in line and "10 unpaired" in line for line in lines)
    assert any("Action gaps: 3 internal skill-to-skill gaps exceeded 2.5s" in line for line in lines)
    assert any("largest 6.1s" in line and "8.6s total beyond" in line for line in lines)
    assert "Gap context: 1 raid-quiet, 1 raid-active, 1 unresolved. Raid activity is context, not proof of cause." in lines
    assert any("63.2% (Trap) to 80.0% (Burning Embers)" in line for line in lines)
    assert "Top damage source: Whip at 23.4% of total damage." in lines
    assert "Review first: 10 eligible skill casts had no observed preceding Light Attack." in lines
    assert not any("good" in line.casefold() or "bad" in line.casefold() for line in lines)


def test_dd_readout_reports_no_long_internal_gap_when_none_exceeds_threshold() -> None:
    lines = _dd_readout_lines(
        _snapshot(
            ObservedActionGapCount=0,
            ObservedLargestActionGapSeconds=None,
            ObservedActionGapExcessSeconds=0.0,
            ActionGapRaidQuietCount=0,
            ActionGapRaidActiveCount=0,
            ActionGapUnknownCount=0,
        )
    )

    assert "No internal eligible skill-to-skill gap exceeded 2.5s." in lines
    assert not any(line.startswith("Action gaps:") for line in lines)
    assert not any(line.startswith("Gap context:") for line in lines)


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
            ObservedActionGapCount=0,
            ObservedLargestActionGapSeconds=None,
            ObservedActionGapExcessSeconds=0.0,
            ActionGapRaidQuietCount=0,
            ActionGapRaidActiveCount=0,
            ActionGapUnknownCount=0,
            ObservedDotUptimes=[],
            TopAbilities=[],
        )
    )

    assert lines == ["No DD diagnostic evidence is available for this snapshot yet."]


def test_dd_readout_does_not_call_action_gaps_dead_time() -> None:
    lines = _dd_readout_lines(_snapshot())

    assert not any("dead time" in line.casefold() for line in lines)


def test_dd_stack_wires_weave_activity_context_and_summary_from_existing_startup_hooks() -> None:
    service_dot = Path("services/performance_dd_dot_support.py").read_text(encoding="utf-8")
    service_weave = Path("services/performance_dd_weave_support.py").read_text(encoding="utf-8")
    service_activity = Path("services/performance_dd_activity_support.py").read_text(encoding="utf-8")
    ui_dot = Path("ui/performance_dashboard_dd_dot_support.py").read_text(encoding="utf-8")
    ui_weave = Path("ui/performance_dashboard_dd_weave_support.py").read_text(encoding="utf-8")
    summary = Path("ui/performance_dashboard_dd_summary_support.py").read_text(encoding="utf-8")

    assert "performance_dd_weave_support" in service_dot
    assert "performance_dd_activity_support" in service_weave
    assert "performance_dd_gap_context_support" in service_activity
    assert "WeaveFightStartTimestampMs" in service_weave
    assert "performance_dashboard_dd_weave_support" in ui_dot
    assert "performance_dashboard_dd_summary_support" in ui_weave
    assert 'FoundryCard("DD Readout")' in summary
    assert "not graded against build-specific targets" in summary
    assert "not graded dead time" in summary
    assert "Raid activity provides context but does not prove why a gap occurred" in summary
    assert '"support_effects_card"' in summary
    assert "_enforce_dd_card_visibility(self, is_dd)" in summary
