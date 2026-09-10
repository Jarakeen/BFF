from pathlib import Path
import subprocess
import sys

from tools.audit_phase13_healer_recast_observation_candidates import (
    _next_phase_time,
    _next_recipient_tick,
    _phase_distance,
    _recipient_shape,
)


def test_next_phase_time_returns_first_old_stream_tick_after_recast():
    assert _next_phase_time(origin=10.0, first_offset=0.05, cadence=1.0, after=12.4) == 13.05


def test_next_recipient_tick_projects_from_last_observed_recipient_tick():
    assert _next_recipient_tick(last_tick=12.05, cadence=1.0, after=12.4) == 13.05


def test_phase_distance_wraps_across_periodic_cadence_boundary():
    assert _phase_distance(first=1.958, second=0.021, cadence=2.0) == pytest.approx(0.063)


def test_recipient_shape_distinguishes_restart_from_old_phase_continuation():
    shape, restart_delta, old_delta = _recipient_shape(
        post_ticks=(12.45, 13.45, 14.45),
        restart_first=12.45,
        old_next=13.05,
        cadence=1.0,
        tolerance=0.1,
    )

    assert shape == "reapplied-restart-shaped"
    assert restart_delta == 0.0
    assert old_delta > 0.1


def test_recipient_shape_flags_both_distinguishable_timing_phases_on_same_target():
    shape, restart_delta, old_delta = _recipient_shape(
        post_ticks=(12.45, 13.05, 13.45),
        restart_first=12.45,
        old_next=13.05,
        cadence=1.0,
        tolerance=0.1,
    )

    assert shape == "both-phases-observed"
    assert restart_delta == 0.0
    assert old_delta == 0.0


def test_recipient_shape_old_phase_only_is_not_treated_as_failed_restart():
    shape, restart_delta, old_delta = _recipient_shape(
        post_ticks=(13.05, 14.05),
        restart_first=12.45,
        old_next=13.05,
        cadence=1.0,
        tolerance=0.1,
    )

    assert shape == "old-phase-only"
    assert restart_delta > 0.1
    assert old_delta == 0.0


def test_recipient_shape_is_ambiguous_when_old_and_new_phases_are_directly_close():
    shape, _, _ = _recipient_shape(
        post_ticks=(12.45, 13.45),
        restart_first=12.45,
        old_next=12.50,
        cadence=1.0,
        tolerance=0.1,
    )

    assert shape == "phase-ambiguous"


def test_recipient_shape_is_ambiguous_when_phases_collide_modulo_cadence():
    shape, restart_delta, old_delta = _recipient_shape(
        post_ticks=(100.021, 102.023),
        restart_first=100.021,
        old_next=101.958,
        cadence=2.0,
        tolerance=0.1,
    )

    assert shape == "phase-ambiguous"
    assert restart_delta == 0.0
    assert old_delta == pytest.approx(0.065)


def test_cli_can_be_executed_directly_from_tools_path():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "audit_phase13_healer_recast_observation_candidates.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--reviewed-observations" in result.stdout
    assert "--fight-id" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
