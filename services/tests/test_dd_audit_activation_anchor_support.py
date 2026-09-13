import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
)
from tools.dd_audit_activation_anchor_support import (
    build_explicit_activation_anchor_resolver,
    parse_explicit_impact_anchor,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(
                time_seconds=10.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Stampede",
                bar="back",
            ),
        ),
    )


def test_parse_explicit_impact_anchor_preserves_exact_action_identity() -> None:
    row = parse_explicit_impact_anchor("Stampede:10:1:10.144")

    assert row.skill_entity_id == "stampede"
    assert row.action_time_seconds == pytest.approx(10.0)
    assert row.action_sequence == 1
    assert row.activation_anchor is PeriodicDamageActivationAnchor.IMPACT
    assert row.anchor_time_seconds == pytest.approx(10.144)
    assert "explicit DD whole-plan audit" in row.source


def test_explicit_impact_anchor_binds_only_to_matching_final_plan_action() -> None:
    plan = _plan()
    exact = parse_explicit_impact_anchor("Stampede:10:1:10.144")
    stale = parse_explicit_impact_anchor("Stampede:9:1:9.144")

    exact_resolver = build_explicit_activation_anchor_resolver(
        plan=plan,
        evidence=(exact,),
    )
    stale_resolver = build_explicit_activation_anchor_resolver(
        plan=plan,
        evidence=(stale,),
    )

    assert exact_resolver is not None
    assert exact_resolver(plan.actions[0], PeriodicDamageActivationAnchor.IMPACT) == pytest.approx(10.144)
    assert stale_resolver is not None
    assert stale_resolver(plan.actions[0], PeriodicDamageActivationAnchor.IMPACT) is None


def test_explicit_impact_anchor_rejects_bad_shape_and_numeric_fields() -> None:
    with pytest.raises(ValueError, match="SKILL:ACTION_TIME:SEQUENCE:IMPACT_TIME"):
        parse_explicit_impact_anchor("Stampede:10:1")

    with pytest.raises(ValueError, match="must be numeric"):
        parse_explicit_impact_anchor("Stampede:ten:1:10.144")
