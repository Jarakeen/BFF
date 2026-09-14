from tools.audit_phase13_xalvakka_add_phase_alignment import (
    PhaseBoundaries,
    classify_phase,
    cluster_wave_times,
    recurrence_intervals,
)


def test_phase_classifier_distinguishes_active_floors_and_transition_downtime():
    boundaries = PhaseBoundaries(
        crossing_70_ms=30_000.0,
        resume_70_ms=80_000.0,
        crossing_40_ms=110_000.0,
        resume_40_ms=175_000.0,
    )

    assert classify_phase(18_000.0, boundaries) == "phase_1"
    assert classify_phase(50_000.0, boundaries) == "transition_70"
    assert classify_phase(90_000.0, boundaries) == "phase_2"
    assert classify_phase(140_000.0, boundaries) == "transition_40"
    assert classify_phase(200_000.0, boundaries) == "phase_3"


def test_daedroth_wave_clustering_groups_near_simultaneous_first_damage_only():
    assert cluster_wave_times((35.794, 36.487, 151.652, 154.201, 217.188), maximum_gap_seconds=5.0) == (
        (35.794, 36.487),
        (151.652, 154.201),
        (217.188,),
    )


def test_recurrence_intervals_are_sorted_and_preserve_observed_variance():
    assert recurrence_intervals((320.171, 18.178, 137.395, 440.974)) == (
        119.217,
        182.77599999999998,
        120.803,
    )
