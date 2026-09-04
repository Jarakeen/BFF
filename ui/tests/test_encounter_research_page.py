from __future__ import annotations

from services.encounter_research_store import EncounterResearchCandidate
from ui.encounter_research_page import filter_candidates


def _candidate(
    candidate_id: str,
    *,
    content: str,
    boss: str,
    fact_type: str,
    status: str,
) -> EncounterResearchCandidate:
    return EncounterResearchCandidate(
        candidate_id=candidate_id,
        source_id="source",
        content_id=content,
        encounter_id=boss,
        fact_type=fact_type,
        fact_key="key",
        value=True,
        evidence_text="evidence",
        status=status,
    )


def test_candidate_filters_are_independent_and_exact() -> None:
    rows = (
        _candidate("a", content="rockgrove", boss="xalvakka", fact_type="phase", status="pending"),
        _candidate("b", content="rockgrove", boss="bahsei", fact_type="interrupt", status="approved"),
        _candidate("c", content="dreadsail_reef", boss="reef_guardian", fact_type="phase", status="pending"),
    )

    assert [row.candidate_id for row in filter_candidates(rows, content_id="rockgrove")] == ["a", "b"]
    assert [row.candidate_id for row in filter_candidates(rows, encounter_id="reef_guardian")] == ["c"]
    assert [row.candidate_id for row in filter_candidates(rows, fact_type="phase", status="pending")] == ["a", "c"]


def test_empty_filters_return_all_candidates() -> None:
    rows = (
        _candidate("a", content="rockgrove", boss="xalvakka", fact_type="phase", status="pending"),
        _candidate("b", content="dreadsail_reef", boss="reef_guardian", fact_type="map", status="deferred"),
    )

    assert filter_candidates(rows) == rows
