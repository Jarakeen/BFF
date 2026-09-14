from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterThresholdClockPoint,
)
from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonPolicyService,
    RotationAssignmentTauntMaintenanceHorizonWindow,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon
from services.rotation_tank_encounter_transition_timing_service import (
    RotationTankEncounterTransitionBoundary,
    RotationTankEncounterTransitionTiming,
)


def _policy(
    *,
    start: float = 0.0,
    source_skill_name="Pierce Armor",
    bar="front",
    end_reference="encounter_end",
):
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        source_skill_name=source_skill_name,
        source="reviewed raid Tank responsibility",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="boss_ownership",
                target_key="boss",
                active_start_seconds=start,
                end_reference=end_reference,
                bar=bar,
            ),
        ),
    )


def _three_phase_policy():
    return RotationAssignmentTauntMaintenanceHorizonPolicy(
        requirement_id="xalvakka:tank:boss_taunt",
        encounter_id="xalvakka",
        requirement_type="taunt",
        source_skill_name="Pierce Armor",
        source="reviewed Xalvakka phase ownership",
        windows=(
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_1",
                target_key="xalvakka",
                active_start_seconds=0.0,
                end_reference="health_threshold:70%",
                bar="front",
            ),
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_2",
                target_key="xalvakka",
                start_reference="transition_resume:70%",
                end_reference="health_threshold:40%",
                bar="front",
            ),
            RotationAssignmentTauntMaintenanceHorizonWindow(
                occurrence_id="phase_3",
                target_key="xalvakka",
                start_reference="transition_resume:40%",
                end_reference="encounter_end",
                bar="front",
            ),
        ),
    )


def _horizon(end=107.116512):
    return RotationTankEncounterHorizon(
        encounter_id="xalvakka",
        end_seconds=end,
        resolved=True,
        evidence=("projected fight end",),
    )


def _point(
    *,
    fact_key="retreat_thresholds",
    fraction=0.70,
    seconds=32.13,
    resolved=True,
):
    return EncounterThresholdClockPoint(
        fact_key=fact_key,
        label=fact_key.replace("_", " ").title(),
        threshold_fraction=fraction,
        time_seconds=seconds if resolved else None,
        resolved=resolved,
        reason="projected from caller-supplied raid damage trajectory",
    )


def _threshold_projection(*, points=None):
    return EncounterHealthThresholdProjection(
        encounter_id="xalvakka",
        difficulty="hardmode",
        maximum_health=214233024,
        trajectory=None,
        points=tuple(points if points is not None else (_point(),)),
        unresolved=(),
    )


def _transition_timing():
    return RotationTankEncounterTransitionTiming(
        encounter_id="xalvakka",
        boundaries=(
            RotationTankEncounterTransitionBoundary(
                threshold_fraction=0.70,
                crossing_time_seconds=32.13,
                resume_time_seconds=80.9395,
                reviewed_delay_seconds=48.8095,
                observed_min_delay_seconds=44.437,
                observed_max_delay_seconds=65.064,
                sample_count=4,
                source="reviewed 70% runtime evidence",
            ),
            RotationTankEncounterTransitionBoundary(
                threshold_fraction=0.40,
                crossing_time_seconds=110.9395,
                resume_time_seconds=175.5005,
                reviewed_delay_seconds=64.561,
                observed_min_delay_seconds=62.266,
                observed_max_delay_seconds=66.376,
                sample_count=3,
                source="reviewed 40% runtime evidence",
            ),
        ),
        adjusted_end_seconds=220.487012,
        resolved=True,
        evidence=("reviewed transition timing",),
    )


def test_resolved_horizon_materializes_existing_numeric_maintenance_policy():
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(),
        horizon=_horizon(),
    )

    assert result.resolved is True
    assert result.policy is not None
    assert result.policy.requirement_id == "xalvakka:tank:boss_taunt"
    assert result.policy.source_skill_name == "Pierce Armor"
    assert result.policy.windows[0].active_start_seconds == 0.0
    assert result.policy.windows[0].active_end_seconds == 107.116512
    assert result.policy.windows[0].target_key == "boss"
    assert result.policy.windows[0].bar == "front"
    assert any("symbolic_endpoint=encounter_end" in row for row in result.evidence)


def test_health_threshold_endpoint_materializes_from_canonical_threshold_clock_point():
    unresolved_fight_end = RotationTankEncounterHorizon(
        encounter_id="xalvakka",
        end_seconds=None,
        resolved=False,
        unresolved=("fight end intentionally unavailable",),
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(end_reference="health_threshold:70%"),
        horizon=unresolved_fight_end,
        health_threshold_projection=_threshold_projection(),
    )

    assert result.resolved is True
    assert result.policy is not None
    assert result.policy.windows[0].active_end_seconds == 32.13
    assert "symbolic_endpoint=health_threshold:70%:32.13" in result.evidence
    assert "threshold_fact=retreat_thresholds" in result.evidence


def test_transition_timing_materializes_three_disjoint_xalvakka_ownership_windows():
    projection = _threshold_projection(
        points=(
            _point(fact_key="retreat_70", fraction=0.70, seconds=32.13),
            _point(fact_key="retreat_40", fraction=0.40, seconds=62.13),
        )
    )
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_three_phase_policy(),
        horizon=_horizon(),
        health_threshold_projection=projection,
        transition_timing=_transition_timing(),
    )

    assert result.resolved is True
    assert result.policy is not None
    assert [
        (window.occurrence_id, window.active_start_seconds, window.active_end_seconds)
        for window in result.policy.windows
    ] == [
        ("phase_1", 0.0, 32.13),
        ("phase_2", 80.9395, 110.9395),
        ("phase_3", 175.5005, 220.487012),
    ]
    assert "symbolic_start=transition_resume:70%:80.9395" in result.evidence
    assert "symbolic_endpoint=health_threshold:40%:110.94" in result.evidence
    assert "symbolic_endpoint=encounter_end_adjusted:220.487" in result.evidence


def test_transition_resume_start_fails_closed_without_reviewed_transition_timing():
    projection = _threshold_projection(
        points=(
            _point(fact_key="retreat_70", fraction=0.70, seconds=32.13),
            _point(fact_key="retreat_40", fraction=0.40, seconds=62.13),
        )
    )
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_three_phase_policy(),
        horizon=_horizon(),
        health_threshold_projection=projection,
    )

    assert result.resolved is False
    assert result.policy is None
    assert "transition timing is unavailable" in result.unresolved[0]


def test_corroborating_same_threshold_facts_may_share_one_projected_endpoint():
    projection = _threshold_projection(
        points=(
            _point(fact_key="retreat_thresholds"),
            _point(fact_key="phase_2"),
        )
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(end_reference="health_threshold:70%"),
        horizon=_horizon(),
        health_threshold_projection=projection,
    )

    assert result.resolved is True
    assert result.policy is not None
    assert result.policy.windows[0].active_end_seconds == 32.13
    assert "threshold_fact=retreat_thresholds" in result.evidence
    assert "threshold_fact=phase_2" in result.evidence


def test_corroborating_same_threshold_facts_must_not_disagree_on_clock_time():
    projection = _threshold_projection(
        points=(
            _point(fact_key="retreat_thresholds", seconds=32.13),
            _point(fact_key="phase_2", seconds=33.13),
        )
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(end_reference="health_threshold:70%"),
        horizon=_horizon(),
        health_threshold_projection=projection,
    )

    assert result.resolved is False
    assert result.policy is None
    assert "disagree on projected clock time" in result.unresolved[0]


def test_health_threshold_endpoint_requires_matching_clock_point():
    projection = _threshold_projection(points=())

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(end_reference="health_threshold:70%"),
        horizon=_horizon(),
        health_threshold_projection=projection,
    )

    assert result.resolved is False
    assert result.policy is None
    assert "no canonical 70%" in result.unresolved[0]


def test_unresolved_health_threshold_endpoint_fails_closed():
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(end_reference="health_threshold:70%"),
        horizon=_horizon(),
        health_threshold_projection=_threshold_projection(points=(_point(resolved=False),)),
    )

    assert result.resolved is False
    assert result.policy is None
    assert "clock point is unresolved" in result.unresolved[0]


def test_unknown_symbolic_endpoint_is_rejected():
    try:
        _policy(end_reference="phase_2_probably")
    except ValueError as exc:
        assert "encounter_end" in str(exc)
        assert "health_threshold" in str(exc)
    else:
        raise AssertionError("unreviewed symbolic endpoint must fail closed")


def test_unknown_symbolic_start_reference_is_rejected():
    try:
        RotationAssignmentTauntMaintenanceHorizonWindow(
            occurrence_id="phase_2",
            target_key="xalvakka",
            start_reference="after_stairs_probably",
            end_reference="encounter_end",
        )
    except ValueError as exc:
        assert "transition_resume" in str(exc)
    else:
        raise AssertionError("unreviewed symbolic start must fail closed")


def test_skill_agnostic_symbolic_policy_binds_canonical_provider_skill_and_bar():
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(source_skill_name=None, bar=None),
        horizon=_horizon(),
        provider_source_skill_name="Inner Rage",
        provider_source_bar="back",
    )

    assert result.resolved is True
    assert result.policy is not None
    assert result.policy.source_skill_name == "Inner Rage"
    assert result.policy.windows[0].bar == "back"
    assert "provider_taunt=Inner Rage" in result.evidence
    assert "provider_taunt_bar=back" in result.evidence


def test_skill_agnostic_symbolic_policy_fails_closed_without_provider_skill():
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(source_skill_name=None, bar=None),
        horizon=_horizon(),
    )

    assert result.resolved is False
    assert result.policy is None
    assert "no exact canonical provider taunt skill" in result.unresolved[0]


def test_reviewed_skill_and_provider_skill_must_not_conflict():
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(),
        horizon=_horizon(),
        provider_source_skill_name="Inner Rage",
        provider_source_bar="back",
    )

    assert result.resolved is False
    assert result.policy is None
    assert "does not match canonical provider taunt" in result.unresolved[0]


def test_unresolved_horizon_fails_closed_without_numeric_policy():
    horizon = RotationTankEncounterHorizon(
        encounter_id="xalvakka",
        end_seconds=None,
        resolved=False,
        unresolved=("damage trajectory ends before boss death",),
    )

    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(),
        horizon=horizon,
    )

    assert result.resolved is False
    assert result.policy is None
    assert result.unresolved == ("damage trajectory ends before boss death",)


def test_horizon_encounter_identity_must_match_policy():
    horizon = RotationTankEncounterHorizon(
        encounter_id="taleria",
        end_seconds=30.0,
        resolved=True,
    )

    try:
        RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
            policy=_policy(),
            horizon=horizon,
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("foreign encounter horizon must fail closed")


def test_projected_end_must_follow_reviewed_maintenance_start():
    result = RotationAssignmentTauntMaintenanceHorizonPolicyService().materialize(
        policy=_policy(start=20.0),
        horizon=_horizon(end=20.0),
    )

    assert result.resolved is False
    assert result.policy is None
    assert "does not occur after" in result.unresolved[0]
