from __future__ import annotations

from types import SimpleNamespace

from services.extreme_maximum_healing_event_record_adapter import (
    ExtremeMaximumHealingEventRecordAdapter,
)
from services.extreme_record_result import ExtremeRecordProofStatus


class _Relevance:
    def classify(self, unresolved):
        values = tuple(unresolved or ())
        return SimpleNamespace(
            relevant=tuple(value for value in values if value == "leader blocker"),
            setup_prerequisites=tuple(
                value for value in values if value == "summon pet first"
            ),
            ambient=tuple(value for value in values if value == "ambient"),
        )


class _Bounds:
    def bound(self, entry):
        upper = getattr(entry, "upper_bound", entry.event_value)
        return SimpleNamespace(
            lower_bound=entry.event_value,
            upper_bound=upper,
            reason=getattr(entry, "bound_reason", ""),
        )


def _entry(
    name,
    value,
    *,
    unresolved=(),
    upper_bound=None,
    optimized_build=None,
):
    route_entry = SimpleNamespace(
        route=SimpleNamespace(equipped_skill_lines=("aedric_spear", "storm_calling", "daedric_summoning")),
        optimization=SimpleNamespace(optimized_build=optimized_build),
        candidate_build="candidate-build",
    )
    return SimpleNamespace(
        source_name=name,
        source_kind="ordinary_skill",
        event_value=value,
        event_kind="canonical_maximum",
        unresolved=tuple(unresolved),
        route_entry=route_entry,
        route=route_entry.route,
        upper_bound=value if upper_bound is None else upper_bound,
        bound_reason="source-supported ceiling",
    )


def _result(*entries, errors=(), omitted=("whole-build optimization outside finalists",)):
    scored = tuple(entry for entry in entries if entry.event_value is not None)
    return SimpleNamespace(
        best_scored=scored[0] if scored else None,
        entries=tuple(entries),
        errors=tuple(errors),
        search_scope=("Stage 2 finalists",),
        omitted_scope=tuple(omitted),
        selection=SimpleNamespace(screened_scored_entries=9660),
    )


def test_stage2_leader_is_lower_bound_not_global_proof():
    leader = _entry(
        "Summon Twilight Matriarch",
        21854.398,
        unresolved=("summon pet first", "ambient"),
        optimized_build="winner-build",
    )
    record = ExtremeMaximumHealingEventRecordAdapter(
        relevance=_Relevance(), bounds=_Bounds()
    ).adapt(_result(leader))

    assert record.objective_key == "actual_heal"
    assert record.raw_value == 21854.398
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.winning_build == "winner-build"
    assert record.runtime_prerequisites == ("summon pet first",)
    assert record.unresolved == ()
    assert record.search_coverage.candidates_screened == 9660
    assert record.search_coverage.candidates_optimized == 1
    assert not record.search_coverage.denominator_proven
    assert not record.globally_proven


def test_stage2_preserves_ceiling_threats_that_can_overtake_leader():
    leader = _entry("Summon Twilight Matriarch", 21854.398)
    challenger = _entry(
        "Blood of the Elder Dragon",
        17870.761,
        unresolved=("leader blocker",),
        upper_bound=26806.142,
    )
    record = ExtremeMaximumHealingEventRecordAdapter(
        relevance=_Relevance(), bounds=_Bounds()
    ).adapt(_result(leader, challenger))

    assert len(record.ceiling_threats) == 1
    threat = record.ceiling_threats[0]
    assert threat.source == "Blood of the Elder Dragon"
    assert threat.lower_bound == 17870.761
    assert threat.upper_bound == 26806.142
    assert threat.reason == "source-supported ceiling"


def test_stage2_ignores_bounded_uncertainty_that_cannot_overtake_leader():
    leader = _entry("Summon Twilight Matriarch", 21854.398)
    harmless = _entry("Other Heal", 10000.0, upper_bound=15000.0)
    record = ExtremeMaximumHealingEventRecordAdapter(
        relevance=_Relevance(), bounds=_Bounds()
    ).adapt(_result(leader, harmless))

    assert record.ceiling_threats == ()


def test_stage2_preserves_leader_relevant_unresolved_and_finalist_errors():
    leader = _entry(
        "Summon Twilight Matriarch",
        21854.398,
        unresolved=("leader blocker", "summon pet first", "ambient"),
    )
    record = ExtremeMaximumHealingEventRecordAdapter(
        relevance=_Relevance(), bounds=_Bounds()
    ).adapt(_result(leader, errors=("one finalist failed",)))

    assert record.unresolved == ("leader blocker", "one finalist failed")
    assert record.runtime_prerequisites == ("summon pet first",)


def test_stage2_without_scored_leader_returns_unresolved_record():
    record = ExtremeMaximumHealingEventRecordAdapter(
        relevance=_Relevance(), bounds=_Bounds()
    ).adapt(_result(errors=("nothing scored",)))

    assert record.raw_value is None
    assert record.proof_status is ExtremeRecordProofStatus.UNRESOLVED
    assert "Stage-2 maximum-healing search produced no scored leader" in record.unresolved
    assert "nothing scored" in record.unresolved
