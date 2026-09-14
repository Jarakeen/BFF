from minmax.status_effect_chance import StatusEffectChanceSource
from services.status_application_opportunity_service import (
    StatusApplicationOpportunityService,
)


def test_force_shock_all_proc_ceiling_exposes_three_statuses_per_cast():
    cast_times = (
        2.0, 3.0, 4.0, 5.0, 6.0,
        8.0, 9.0, 10.0, 11.0, 12.0,
        14.0, 15.0, 16.0, 17.0, 18.0,
        20.0, 21.0, 22.0,
    )
    result = StatusApplicationOpportunityService.from_damage_casts(
        cast_times=cast_times,
        damage_types=("flame", "frost", "shock"),
        source_family=StatusEffectChanceSource.SINGLE_TARGET_DIRECT,
        increase_percent=100.0,
        source_name="Force Shock",
        score_seconds=24.999,
    )

    assert result.denominator_proven is True
    assert result.all_procs_application_ceiling == 54
    assert result.deterministic_application_count == 0
    assert round(result.expected_application_count, 3) == 10.8
    assert result.all_procs_is_stochastic is True
    assert {row.status_name for row in result.opportunities} == {
        "Burning",
        "Chilled",
        "Concussion",
    }
    assert {round(row.chance, 3) for row in result.opportunities} == {0.2}


def test_unknown_damage_type_fails_closed_without_inventing_status():
    result = StatusApplicationOpportunityService.from_damage_casts(
        cast_times=(1.0,),
        damage_types=("oblivion",),
        source_family=StatusEffectChanceSource.SINGLE_TARGET_DIRECT,
        source_name="unknown",
        score_seconds=2.0,
    )

    assert result.denominator_proven is False
    assert result.all_procs_application_ceiling == 0
    assert result.unresolved == (
        "unreviewed status mapping for damage type: 'oblivion'",
    )


def test_out_of_window_cast_is_rejected_from_ceiling():
    result = StatusApplicationOpportunityService.from_damage_casts(
        cast_times=(1.0, 3.0),
        damage_types=("flame",),
        source_family=StatusEffectChanceSource.SINGLE_TARGET_DIRECT,
        source_name="test",
        score_seconds=2.0,
    )

    assert result.all_procs_application_ceiling == 1
    assert result.denominator_proven is False
    assert "exceeds score window" in result.unresolved[0]
