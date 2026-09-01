from tools.audit_phase6_resource_event_candidates import (
    ResourceEventCandidateAuditRow,
    summarize,
)


def _row(*, promoted: bool, resources: tuple[str, ...] = ()) -> ResourceEventCandidateAuditRow:
    return ResourceEventCandidateAuditRow(
        skill_rank_id=10,
        coefficient_number=1,
        ability_id=100,
        ability_name="Fixture",
        promoted=promoted,
        resources=resources,
        phase3_reasons=("effect_kind",),
        fragment="Restore $1 Magicka.",
    )


def test_summary_separates_promoted_and_unresolved_candidates():
    summary = summarize(
        (
            _row(promoted=True, resources=("magicka",)),
            _row(promoted=False),
            _row(promoted=True, resources=("stamina",)),
        )
    )

    assert summary["candidates"] == 3
    assert summary["promoted"] == 2
    assert summary["unresolved"] == 1
    assert summary["resources"]["magicka"] == 1
    assert summary["resources"]["stamina"] == 1


def test_empty_candidate_summary_is_zeroed():
    summary = summarize(())

    assert summary["candidates"] == 0
    assert summary["promoted"] == 0
    assert summary["unresolved"] == 0
    assert not summary["resources"]
