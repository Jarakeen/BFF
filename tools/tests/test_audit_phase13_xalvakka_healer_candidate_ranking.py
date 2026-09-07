from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from tools.audit_phase13_xalvakka_healer_candidate_ranking import (
    _has_required_action_candidate,
)


def _candidate(*actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=60.0,
            actions=actions,
        ),
        refresh_leads=(),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Xalvakka Phase 2 healing prep",
        start_seconds=29.1349536,
        end_seconds=34.1349536,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def test_existing_exact_action_suppresses_unnecessary_claim_and_rescue() -> None:
    candidates = (
        _candidate(
            RotationAction(
                31.0,
                0,
                RotationActionKind.SKILL,
                "Budding Seeds",
                "front",
            )
        ),
    )

    assert _has_required_action_candidate(
        candidates,
        demand=_demand(),
        skill_name="Budding Seeds",
        bar="front",
    )


def test_wrong_time_bar_or_skill_does_not_suppress_required_rescue() -> None:
    candidates = (
        _candidate(
            RotationAction(
                36.0,
                0,
                RotationActionKind.SKILL,
                "Budding Seeds",
                "front",
            )
        ),
        _candidate(
            RotationAction(
                31.0,
                0,
                RotationActionKind.SKILL,
                "Budding Seeds",
                "back",
            )
        ),
        _candidate(
            RotationAction(
                31.0,
                0,
                RotationActionKind.SKILL,
                "Combat Prayer",
                "front",
            )
        ),
    )

    assert not _has_required_action_candidate(
        candidates,
        demand=_demand(),
        skill_name="Budding Seeds",
        bar="front",
    )
