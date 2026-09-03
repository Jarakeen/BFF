from services.encounter_evidence import ReconciledEncounterFact
from tools.audit_encounter_timeline_evidence import timeline_trigger_kind


def _fact(*, fact_type: str, value, status: str = "corroborated") -> ReconciledEncounterFact:
    return ReconciledEncounterFact(
        encounter_id="boss",
        fact_type=fact_type,
        fact_key="example",
        status=status,
        value=value,
        evidence=(),
        distinct_sources=2,
        distinct_values=1 if status != "conflicting" else 2,
    )


def test_timeline_trigger_kind_recognizes_health_thresholds() -> None:
    fact = _fact(fact_type="transition", value={"thresholds": ["90%", "50%"]})

    assert timeline_trigger_kind(fact) == "health_threshold"


def test_timeline_trigger_kind_keeps_phase_as_phase() -> None:
    fact = _fact(fact_type="phase", value={"label": "Execute"})

    assert timeline_trigger_kind(fact) == "phase"


def test_timeline_trigger_kind_recognizes_observation_shapes_without_conflating_them() -> None:
    assert timeline_trigger_kind(
        _fact(fact_type="transition", value={"exact_time_seconds": 30})
    ) == "exact_time"
    assert timeline_trigger_kind(
        _fact(fact_type="transition", value={"timing_window_seconds": [34, 39]})
    ) == "approx_time"
    assert timeline_trigger_kind(
        _fact(fact_type="transition", value={"repeat_interval_seconds": 20})
    ) == "repeat_interval"


def test_timeline_trigger_kind_never_resolves_conflicting_fact() -> None:
    fact = _fact(
        fact_type="transition",
        value=None,
        status="conflicting",
    )

    assert timeline_trigger_kind(fact) == "conflicting"


def test_timeline_trigger_kind_ignores_non_timeline_fact_types() -> None:
    fact = _fact(fact_type="mechanic_detail", value={"thresholds": ["50%"]})

    assert timeline_trigger_kind(fact) is None
