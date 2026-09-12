from __future__ import annotations

from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
)
from tools.discover_rotation_dd_periodic_esologs_stable_controls import (
    StableControlGroup,
    rank_stable_controls,
)


def _group(
    report_code: str,
    *,
    fight_id: int = 1,
    source_id: int = 1,
    comparable: int,
    same_changed: int,
    same_constant: int,
    changed_changed: int = 0,
    changed_constant: int = 0,
    ambiguous: int = 0,
) -> StableControlGroup:
    return StableControlGroup(
        report_code=report_code,
        fight_id=fight_id,
        source_id=source_id,
        cast_count=4,
        report=RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport(
            skill_entity_id="stampede",
            periodic_ability_id=126474,
            comparable_occurrence_pairs=comparable,
            state_changed_amount_changed=changed_changed,
            state_changed_amount_constant=changed_constant,
            state_same_amount_changed=same_changed,
            state_same_amount_constant=same_constant,
            ambiguous_occurrence_clusters=ambiguous,
        ),
    )


def test_rank_prefers_more_stable_state_pairs() -> None:
    noisy = _group("NOISY", comparable=20, same_changed=0, same_constant=1)
    stable = _group("STABLE", comparable=10, same_changed=0, same_constant=5)

    ranked = rank_stable_controls((noisy, stable))

    assert [item.report_code for item in ranked] == ["STABLE", "NOISY"]


def test_rank_prefers_constant_stable_controls_over_changed_amounts() -> None:
    suspicious = _group("SUSPICIOUS", comparable=8, same_changed=3, same_constant=1)
    control = _group("CONTROL", comparable=8, same_changed=0, same_constant=4)

    ranked = rank_stable_controls((suspicious, control))

    assert [item.report_code for item in ranked] == ["CONTROL", "SUSPICIOUS"]
