from minmax.dd_damage import DDDamageEvent
from services.rotation_dd_action_damage_event_service import RotationDDDotComponentSeed
from services.rotation_dd_dot_runtime_catalog import (
    WINTERS_REVENGE_SOURCE,
    u50_winters_revenge_runtime_evidence,
)
from services.rotation_dd_dot_runtime_service import RotationDDDotRuntimeService


def _seed(time_seconds=0.0, sequence=1, coefficient_number=7):
    return RotationDDDotComponentSeed(
        cast_time_seconds=time_seconds,
        sequence=sequence,
        source_name=WINTERS_REVENGE_SOURCE,
        coefficient_number=coefficient_number,
        event=DDDamageEvent(
            base_value=321.0,
            damage_type="frost",
            can_crit=True,
            is_dot=True,
            is_aoe=True,
        ),
    )


def test_u50_winters_revenge_catalog_preserves_reviewed_timing_and_provenance():
    evidence = u50_winters_revenge_runtime_evidence(coefficient_number=7)

    assert evidence.source_name == WINTERS_REVENGE_SOURCE
    assert evidence.coefficient_number == 7
    assert evidence.duration_seconds == 12.0
    assert evidence.tick_interval_seconds == 1.0
    assert evidence.first_tick_offset_seconds == 1.0
    assert evidence.tick_on_expiry_boundary is True
    assert evidence.refresh_behavior_verified is False
    assert any("BTVTools" in item and "U50" in item for item in evidence.provenance)


def test_single_winters_revenge_application_projects_twelve_reviewed_ticks():
    evidence = u50_winters_revenge_runtime_evidence(coefficient_number=7)
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(),),
        evidence=(evidence,),
        horizon_seconds=20.0,
    )

    assert result.unresolved == ()
    assert [event.time_seconds for event in result.events] == [
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        7.0,
        8.0,
        9.0,
        10.0,
        11.0,
        12.0,
    ]
    assert all(event.event.damage_type == "frost" for event in result.events)
    assert all(event.event.is_dot is True for event in result.events)
    assert all(event.event.is_aoe is True for event in result.events)


def test_repeated_winters_revenge_casts_fail_closed_without_refresh_proof():
    evidence = u50_winters_revenge_runtime_evidence(coefficient_number=7)
    result = RotationDDDotRuntimeService().project(
        seeds=(_seed(0.0, 1), _seed(10.0, 2)),
        evidence=(evidence,),
        horizon_seconds=30.0,
    )

    assert result.events == ()
    assert result.unresolved == (
        "Winter's Revenge coefficient 7: DoT refresh behavior is not canonically verified",
    )
