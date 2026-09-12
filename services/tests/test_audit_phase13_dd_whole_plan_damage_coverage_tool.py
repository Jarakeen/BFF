import json

from minmax.rotation_plan import RotationActionKind
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDDamageCoverageBlocker,
    RotationDDWholePlanDamageCoverageAudit,
)
from tools.audit_phase13_dd_whole_plan_damage_coverage import (
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
