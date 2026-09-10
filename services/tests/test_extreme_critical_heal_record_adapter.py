from __future__ import annotations

from types import SimpleNamespace

from services.extreme_critical_heal_record_adapter import ExtremeCriticalHealRecordAdapter
from services.extreme_record_result import ExtremeRecordProofStatus


def _leader(
    *,
    value=32100.0,
    unresolved=(),
    mechanic_complete=True,
    optimized_build=None,
):
    return SimpleNamespace(
        critical_heal=value,
        unresolved=tuple(unresolved),
        mechanic_complete=mechanic_complete,
        candidate=SimpleNamespace(name="Absurd Heal"),
        route=SimpleNamespace(equipped_skill_lines=("restoring_light", "green_balance", "living_death")),
        candidate_build={"kind": "candidate"},
        optimization=SimpleNamespace(optimized_build=optimized_build),
    )


def _result(*, leader, entries=None, omitted=("runtime conditional stacks/procs",), proven=False):
    entries = tuple(entries if entries is not None else (() if leader is None else (leader,)))
    return SimpleNamespace(
        best_scored=leader,
        entries=entries,
        search_scope=("critical-capable ordinary healing events",),
        omitted_scope=tuple(omitted),
        global_maximum_proven=bool(proven),
    )


def test_adapts_current_critical_heal_leader_as_lower_bound_when_denominator_is_open():
    leader = _leader(value=32123.5)
    record = ExtremeCriticalHealRecordAdapter().adapt(_result(leader=leader))

    assert record.objective_key == "critical_heal"
    assert record.raw_value == 32123.5
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert not record.globally_proven
    assert record.search_coverage.candidates_screened == 1
    assert record.search_coverage.candidates_optimized == 1
    assert not record.search_coverage.denominator_proven


def test_preserves_optimized_winning_build_snapshot():
    winning_build = {"race": "argonian", "purpose": "crime"}
    leader = _leader(optimized_build=winning_build)
    record = ExtremeCriticalHealRecordAdapter().adapt(_result(leader=leader))

    assert record.winning_build is winning_build


def test_setup_prerequisites_do_not_become_unresolved_mechanics():
    leader = _leader(
        unresolved=(
            "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive",
            "Potion selected; activation/uptime is not part of static build state: spell power",
        )
    )
    record = ExtremeCriticalHealRecordAdapter().adapt(_result(leader=leader))

    assert len(record.runtime_prerequisites) == 2
    assert record.unresolved == ()
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND


def test_can_promote_to_proven_only_when_source_catalog_proves_the_denominator():
    leader = _leader(value=40000.0)
    record = ExtremeCriticalHealRecordAdapter().adapt(
        _result(leader=leader, omitted=(), proven=True)
    )

    assert record.proof_status is ExtremeRecordProofStatus.PROVEN
    assert record.search_coverage.denominator_proven
    assert record.globally_proven


def test_no_scored_critical_event_is_unresolved_not_zero():
    record = ExtremeCriticalHealRecordAdapter().adapt(_result(leader=None, entries=(), omitted=()))

    assert record.raw_value is None
    assert record.proof_status is ExtremeRecordProofStatus.UNRESOLVED
    assert "no scored critical event" in record.unresolved[0].casefold()
