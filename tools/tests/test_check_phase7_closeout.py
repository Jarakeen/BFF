from dataclasses import replace

from minmax.skill_component_runtime_timing import RuntimeCadenceBoundKind
from tools import check_phase7_closeout as closeout


def test_runtime_capability_inventory_covers_phase7_exit_surface():
    assert closeout.RUNTIME_CAPABILITIES == (
        "shared_runtime_event_contract",
        "component_timing_and_state_binding",
        "effect_trigger_eligibility",
        "deterministic_proc_chance",
        "global_and_target_cooldowns",
        "active_duration_windows",
        "stacking_and_refresh",
        "ordered_effect_streams",
        "status_effect_runtime_state",
        "triggered_resource_restoration",
        "triggered_healing",
        "target_count_and_explicit_selection",
    )


def test_real_phase7_closeout_gate_passes_current_database():
    result = closeout.evaluate_phase7_closeout(closeout.DEFAULT_DATABASE)

    assert result["passed"]
    assert result["failures"] == ()
    assert result["timing_unresolved"] == ()

    summary = result["boundary_summary"]
    assert summary["trigger_resolution"] == 0
    assert summary["runtime_review"] == 0

    kinds = result["timing_kinds"]
    assert sum(kinds.values()) == len(result["rows"])
    assert kinds[RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW.value] > 0
    assert kinds[RuntimeCadenceBoundKind.FIXED_COUNT_DURATION.value] > 0
    assert kinds[RuntimeCadenceBoundKind.STACK_COUNT.value] > 0


def test_closeout_fails_when_boundary_needs_trigger_resolution(monkeypatch):
    row = _fake_row(runtime_concerns=("trigger_resolution", "cadence"))
    monkeypatch.setattr(closeout, "load_phase7_runtime_boundaries", lambda _database: (row,))
    monkeypatch.setattr(
        closeout,
        "extract_skill_component_runtime_timing",
        lambda _fragment: _fake_timing(),
    )

    result = closeout.evaluate_phase7_closeout("unused.db")

    assert not result["passed"]
    assert result["failures"] == (
        "1 boundary row(s) still need canonical trigger resolution",
    )


def test_closeout_fails_when_timing_is_unresolved(monkeypatch):
    row = _fake_row(runtime_concerns=("cadence",))
    monkeypatch.setattr(closeout, "load_phase7_runtime_boundaries", lambda _database: (row,))
    monkeypatch.setattr(closeout, "extract_skill_component_runtime_timing", lambda _fragment: None)

    result = closeout.evaluate_phase7_closeout("unused.db")

    assert not result["passed"]
    assert result["timing_unresolved"] == (row,)
    assert result["failures"] == (
        "1 boundary row(s) lack canonical timing semantics",
    )


def _fake_row(*, runtime_concerns):
    from tools.audit_phase7_runtime_boundaries import Phase7RuntimeBoundaryRow

    return Phase7RuntimeBoundaryRow(
        skill_rank_id=1,
        coefficient_number=1,
        ability_id=1,
        ability_name="Test Ability",
        trigger_types=(),
        runtime_concerns=runtime_concerns,
        reason="test",
        signals=(),
        fragment="deals damage every 2 seconds",
    )


def _fake_timing():
    from minmax.skill_component_runtime_timing import SkillComponentRuntimeTiming

    return SkillComponentRuntimeTiming(
        bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
        evidence="every 2 seconds",
        interval_seconds=2.0,
    )
