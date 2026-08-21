from minmax.dd_mitigation import (
    DDMitigationResult,
    calculate_dd_mitigation,
)


def test_mitigation_result_is_returned():
    result = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=0,
    )

    assert isinstance(result, DDMitigationResult)


def test_penetration_reduces_remaining_resistance():
    result = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=5000,
    )

    assert result.remaining_resistance == 13200


def test_trial_boss_resistance_produces_36_4_percent_mitigation():
    result = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=0,
    )

    assert result.mitigation_fraction == 0.364
    assert result.damage_multiplier == 0.636


def test_penetration_to_resistance_cap_removes_mitigation():
    result = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=18200,
    )

    assert result.remaining_resistance == 0
    assert result.mitigation_fraction == 0
    assert result.damage_multiplier == 1


def test_overpenetration_does_not_create_negative_resistance():
    result = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=20000,
    )

    assert result.remaining_resistance == 0
    assert result.mitigation_fraction == 0
    assert result.damage_multiplier == 1


def test_custom_resistance_conversion_can_be_used():
    result = calculate_dd_mitigation(
        target_resistance=6600,
        penetration=0,
        resistance_per_percent=660,
    )

    assert result.mitigation_fraction == 0.10
    assert result.damage_multiplier == 0.90


def test_negative_target_resistance_is_rejected():
    try:
        calculate_dd_mitigation(
            target_resistance=-1,
            penetration=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Negative target resistance should be rejected."
        )


def test_negative_penetration_is_rejected():
    try:
        calculate_dd_mitigation(
            target_resistance=10000,
            penetration=-1,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Negative penetration should be rejected."
        )