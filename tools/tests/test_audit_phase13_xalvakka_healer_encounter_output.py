from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from tools.audit_phase13_xalvakka_healer_encounter_output import (
    _candidate,
    _load_reviewed_runtime_observations,
    _window_actions,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=9.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Before",
                bar="front",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=1,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=2,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                time_seconds=11.5,
                sequence=3,
                kind=RotationActionKind.SKILL,
                name="Energy Orb",
                bar="back",
            ),
            RotationAction(
                time_seconds=12.0,
                sequence=4,
                kind=RotationActionKind.SKILL,
                name="Boundary",
                bar="front",
            ),
        ),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Xalvakka Phase 2 healing prep",
        start_seconds=10.0,
        end_seconds=12.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def test_candidate_wraps_exact_plan_without_rescheduling():
    plan = _plan()
    candidate = _candidate("xalvakka-aware", plan)

    assert candidate.candidate_id == "xalvakka-aware"
    assert candidate.plan is plan
    assert candidate.refresh_leads == ()
    assert candidate.action_claims == ()


def test_window_trace_excludes_light_attacks_and_end_boundary():
    actions = _window_actions(_plan(), _demand())

    assert [(action.time_seconds, action.name, action.bar) for action in actions] == [
        (10.0, "Combat Prayer", "front"),
        (11.5, "Energy Orb", "back"),
    ]


def test_missing_runtime_fixture_means_no_observations_are_invented():
    observations, unresolved = _load_reviewed_runtime_observations(
        database_path=None,
        fixture_path=None,
    )

    assert observations == ()
    assert unresolved == ()
