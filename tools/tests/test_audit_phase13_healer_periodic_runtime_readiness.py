from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingResolution,
)
from services.rotation_healer_saved_build_periodic_timing_service import (
    RotationHealerSavedBuildPeriodicTimingEntry,
)
from tools.audit_phase13_healer_periodic_runtime_readiness import (
    _render_entry,
    runtime_facts_still_required,
)


def _entry(
    *,
    cadence=1.0,
    duration=6.0,
    unresolved=(),
    skill_name="Budding Seeds",
    coefficient_number=2,
):
    timing = None
    if cadence is not None:
        timing = SkillComponentRuntimeTiming(
            bound_kind=RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW,
            interval_seconds=cadence,
            evidence=f"every {cadence:g} second",
        )
    return RotationHealerSavedBuildPeriodicTimingEntry(
        bar="front",
        slot=2,
        skill_name=skill_name,
        coefficient_number=coefficient_number,
        timing=RotationHealerCanonicalPeriodicTimingResolution(
            source_name=skill_name,
            coefficient_number=coefficient_number,
            skill_rank_id=123,
            ability_id=456,
            component_fragment="periodic heal fragment",
            timing=timing,
            duration_seconds=duration,
            evidence=("canonical cadence evidence",),
            unresolved=tuple(unresolved),
        ),
    )


def test_canonical_cadence_and_duration_do_not_remove_runtime_semantic_gaps():
    gaps = runtime_facts_still_required(_entry())

    assert "periodic cadence" not in gaps
    assert "active duration" not in gaps
    assert gaps == (
        "first-tick offset from cast/application",
        "tick-at-expiry boundary behavior",
        "second-activation bloom scheduling / periodic termination boundary",
    )


def test_missing_cadence_is_reported_separately():
    gaps = runtime_facts_still_required(_entry(cadence=None))

    assert gaps[0] == "periodic cadence"
    assert "active duration" not in gaps


def test_missing_duration_is_reported_separately():
    gaps = runtime_facts_still_required(_entry(duration=None))

    assert "periodic cadence" not in gaps
    assert gaps[0] == "active duration"


def test_unknown_reapplication_topology_keeps_generic_refresh_gap():
    gaps = runtime_facts_still_required(
        _entry(skill_name="Echoing Vigor", coefficient_number=1, cadence=2.0, duration=16.0)
    )

    assert gaps[-1] == "refresh/recast behavior for repeated applications"


def test_one_active_topology_reports_boundary_instead_of_fake_restart():
    gaps = runtime_facts_still_required(
        _entry(skill_name="Illustrious Healing", coefficient_number=1, cadence=2.0, duration=15.0)
    )

    assert gaps[-1] == "one-active-instance replacement/termination boundary"


def test_render_preserves_bar_slot_canonical_and_reapplication_evidence():
    lines = _render_entry(_entry())
    rendered = "\n".join(lines)

    assert "[front slot 2] Budding Seeds coefficient 2" in rendered
    assert "cadence:  1s" in rendered
    assert "duration: 6s" in rendered
    assert "explicit_state_window" in rendered
    assert "canonical cadence evidence" in rendered
    assert "reapplication topology: second_activation_special" in rendered
    assert "instantly bloom" in rendered


def test_render_preserves_canonical_unresolved_without_collapsing_runtime_gaps():
    lines = _render_entry(_entry(unresolved=("component duration ambiguous",)))
    rendered = "\n".join(lines)

    assert "canonical unresolved:" in rendered
    assert "component duration ambiguous" in rendered
    assert "runtime facts still required:" in rendered
    assert "second-activation bloom scheduling / periodic termination boundary" in rendered
