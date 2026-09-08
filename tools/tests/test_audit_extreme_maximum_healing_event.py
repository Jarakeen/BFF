from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild
from services.extreme_maximum_healing_event_explanation_service import (
    ExtremeMaximumHealingEventTrace,
)
from tools.audit_extreme_maximum_healing_event import _find_build, format_report


def _build(name="DF Healer"):
    return PlayerBuild(Name="Magrat", BuildName=name, EsoClass="warden")


def _entry(*, name, value, source_kind, slot=0, complete=True):
    return SimpleNamespace(
        source_name=name,
        source_kind=source_kind,
        event_value=float(value),
        event_kind="canonical_maximum" if source_kind == "ordinary_skill" else "normal_noncritical",
        mechanic_complete=complete,
        unresolved=() if complete else ("entry unresolved",),
        route=SimpleNamespace(equipped_skill_lines=("green_balance", "winters_embrace", "animal_companions")),
        slotted_index=slot,
        trace=ExtremeMaximumHealingEventTrace(
            coefficient_numbers=(3,) if source_kind == "ordinary_skill" else (),
            recipient_scopes=("group",) if source_kind == "ordinary_skill" else ("self",),
            recipient_keys=("friendly_targets",) if source_kind == "ordinary_skill" else ("caster",),
            event_keys=("pet_special_activation",) if source_kind == "ordinary_skill" else ("blood_magic_costed_dark_magic_trigger",),
            temporal_scopes=("direct",),
        ),
    )


def test_find_build_matches_build_name_case_insensitively():
    build = _build()
    assert _find_build((build,), "df healer") is build


def test_find_build_rejects_missing_or_ambiguous_names():
    with pytest.raises(ValueError, match="Saved build not found"):
        _find_build((_build(),), "missing")
    with pytest.raises(ValueError, match="Ambiguous build name"):
        _find_build((_build(), _build()), "DF Healer")


def test_report_prints_winner_identity_margin_and_proof_boundaries():
    winner = _entry(name="Twilight Matriarch", value=18000, source_kind="ordinary_skill", slot=1)
    runner = _entry(name="Blood Magic via Dark Exchange", value=15000, source_kind="blood_magic", slot=2)
    explanation = SimpleNamespace(
        source_name=winner.source_name,
        event_value=winner.event_value,
        event_kind=winner.event_kind,
        source_kind=winner.source_kind,
        route_skill_lines=winner.route.equipped_skill_lines,
        slotted_index=winner.slotted_index,
        trace=winner.trace,
        runner_up_name=runner.source_name,
        runner_up_value=runner.event_value,
        margin=3000.0,
        reason="Twilight Matriarch wins by 3000.000.",
    )
    result = SimpleNamespace(
        winner_explanation=explanation,
        global_maximum_proven=False,
        entries=(winner, runner),
        omitted_scope=("runtime conditional stacks/procs",),
        search_scope=("unified maximum event ranking",),
    )

    text = format_report(result, build=_build(), active_bar="front", top=2)

    assert "Twilight Matriarch" in text
    assert "Maximum event: 18000.000 (canonical_maximum)" in text
    assert "Recipient: group / friendly_targets" in text
    assert "Winning coefficients: 3" in text
    assert "Runner-up: Blood Magic via Dark Exchange" in text
    assert "Margin: 3000.000" in text
    assert "Global maximum proven: NO" in text
    assert "runtime conditional stacks/procs" in text


def test_report_keeps_unresolved_candidate_visible_in_top_results():
    entry = _entry(name="Unknown Crit Heal", value=12000, source_kind="ordinary_skill", complete=False)
    entry.unresolved = ("critical eligibility unresolved",)
    result = SimpleNamespace(
        winner_explanation=None,
        global_maximum_proven=False,
        entries=(entry,),
        omitted_scope=(),
        search_scope=(),
    )

    text = format_report(result, build=_build(), active_bar="back", top=1)

    assert "No candidate has a proved maximum-event value." in text
    assert "Unknown Crit Heal" in text
    assert "evidence: incomplete" in text
    assert "critical eligibility unresolved" in text
