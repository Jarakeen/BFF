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


def _entry(*, cadence=1.0, duration=6.0, unresolved=()):
    timing = None
    if cadence is not None:
        timing = SkillComponentRuntimeTiming(
            bound_kind=RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW,
            interval_seconds=cadence,
            evidence="every 1 second",
        )
    return RotationHealerSavedBuildPeriodicTimingEntry(
        bar="front",
        slot=2,
        skill_name="Budding Seeds",
        coefficient_number=2,
        timing=RotationHealerCanonicalPeriodicTimingResolution(
            source_name="Budding Seeds",
            coefficient_number=2,
            skill_rank_id=123,
            ability_id=456,
            component_fragment="While the field grows, you and allies are healed every 1 second.",
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
        "refresh/recast behavior for repeated applications",
    )


def test_missing_cadence_is_reported_separately():
    gaps = runtime_facts_still_required(_entry(cadence=None))

    assert gaps[0] == "periodic cadence"
    assert "active duration" not in gaps


def test_missing_duration_is_reported_separately():
    gaps = runtime_facts_still_required(_entry(duration=None))

    assert "periodic cadence" not in gaps
    assert gaps[0] == "active duration"


def test_render_preserves_bar_slot_and_canonical_evidence():
    lines = _render_entry(_entry())
    rendered = "\n".join(lines)

    assert "[front slot 2] Budding Seeds coefficient 2" in rendered
    assert "cadence:  1s" in rendered
    assert "duration: 6s" in rendered
    assert "explicit_state_window" in rendered
    assert "canonical cadence evidence" in rendered


def test_render_preserves_canonical_unresolved_without_collapsing_runtime_gaps():
    lines = _render_entry(_entry(unresolved=("component duration ambiguous",)))
    rendered = "\n".join(lines)

    assert "canonical unresolved:" in rendered
    assert "component duration ambiguous" in rendered
    assert "runtime facts still required:" in rendered
    assert "refresh/recast behavior for repeated applications" in rendered
