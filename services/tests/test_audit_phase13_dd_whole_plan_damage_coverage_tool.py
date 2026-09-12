import json

import pytest

from minmax.rotation_plan import RotationActionKind
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDDamageCoverageBlocker,
    RotationDDWholePlanDamageCoverageAudit,
)
from tools.audit_phase13_dd_whole_plan_damage_coverage import (
    _group_static_prerequisite_gaps,
    _parse_target_window,
    _saved_dd_builds,
    _sorted_blockers,
)


def test_saved_dd_builds_lists_only_damage_roles_in_stable_order(tmp_path) -> None:
    path = tmp_path / "builds.json"
    path.write_text(
        json.dumps(
            {
                "Members": [
                    {"Name": "Zeta", "BuildName": "Heals", "Role": "Healer"},
                    {"Name": "Beta", "BuildName": "Parse", "Role": "DPS"},
                    {"Name": "Alpha", "BuildName": "Trial DD", "Role": "DD"},
                    {"Name": "Alpha", "BuildName": "Support", "Role": "Damage Dealer"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert _saved_dd_builds(path) == (
        ("Alpha", "Support", "Damage Dealer"),
        ("Alpha", "Trial DD", "DD"),
        ("Beta", "Parse", "DPS"),
    )


def test_sorted_blockers_orders_highest_occurrence_count_first() -> None:
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="real-build",
        total_damage_actions=4,
        resolved_damage_actions=1,
        unresolved_damage_actions=3,
        blockers=(
            RotationDDDamageCoverageBlocker(
                action_kind=RotationActionKind.LIGHT_ATTACK,
                action_name=None,
                reason="unsupported weapon family",
                occurrences=((0.0, 0),),
            ),
            RotationDDDamageCoverageBlocker(
                action_kind=RotationActionKind.SKILL,
                action_name="stampede",
                reason="impact timing unresolved",
                occurrences=((1.0, 0), (6.0, 0)),
            ),
        ),
    )

    ranked = _sorted_blockers(audit)

    assert ranked[0].action_name == "stampede"
    assert ranked[0].occurrence_count == 2
    assert ranked[1].action_kind is RotationActionKind.LIGHT_ATTACK


def test_static_prerequisite_gaps_collapse_front_back_duplicates() -> None:
    gaps = _group_static_prerequisite_gaps(
        (
            "front static context: Necklace jewelry trait not yet resolved: Bloodthirsty",
            "back static context: Necklace jewelry trait not yet resolved: Bloodthirsty",
            "front static context: Front Bar Off Hand Charged: requires status-effect chance model",
            "build-level progression evidence missing",
        )
    )

    assert gaps[0].reason == "Necklace jewelry trait not yet resolved: Bloodthirsty"
    assert gaps[0].bars == ("front", "back")
    assert any(
        gap.reason == "Front Bar Off Hand Charged: requires status-effect chance model"
        and gap.bars == ("front",)
        for gap in gaps
    )
    assert any(
        gap.reason == "build-level progression evidence missing"
        and gap.bars == ("build",)
        for gap in gaps
    )


def test_parse_target_window_builds_authoritative_off_balance_window() -> None:
    window = _parse_target_window("5:12")

    assert window.start_seconds == pytest.approx(5.0)
    assert window.end_seconds == pytest.approx(12.0)
    assert window.active_buffs == ("Off Balance",)


def test_parse_target_window_rejects_bad_shape_and_non_numeric_values() -> None:
    with pytest.raises(ValueError, match="START:END"):
        _parse_target_window("5")

    with pytest.raises(ValueError, match="numeric START:END"):
        _parse_target_window("five:twelve")
