from __future__ import annotations

from pathlib import Path

from services.encounter_content_gap_audit import (
    EncounterContentGapAudit,
    EncounterDatabaseCoverage,
    EncounterPacketGap,
)
from tools.audit_encounter_canonical_gaps import _review_backed_rows


def _row(encounter_id: str) -> EncounterDatabaseCoverage:
    return EncounterDatabaseCoverage(
        encounter_id=encounter_id,
        name=encounter_id.title(),
        npc_count=1,
        health_count=1,
        ability_count=8,
        mechanic_count=0,
        phase_count=0,
        dialogue_count=2,
        section_count=3,
        strategy_count=0,
        canonical_fact_count=0,
        canonical_evidence_count=0,
    )


def _packet(encounter_id: str, *, facts: int) -> EncounterPacketGap:
    return EncounterPacketGap(
        packet_path=Path(f"{encounter_id}.json"),
        encounter_id=encounter_id,
        encounter_name=encounter_id.title(),
        reconciled_facts=facts,
        eligible=(),
        review_required=("damage_window:flight",) if facts else (),
        blocked=(),
        persisted=(),
        missing_eligible=(),
    )


def test_review_backed_rows_exclude_structural_only_backlog():
    lokke = _row("lokkestiiz")
    nahvii = _row("nahviintaas")
    audit = EncounterContentGapAudit(
        content_id="sunspire",
        content_name="Sunspire",
        database_encounters=(lokke, nahvii),
        packet_gaps=(
            _packet("lokkestiiz", facts=2),
            _packet("nahviintaas", facts=0),
        ),
        encounters_without_packets=(),
        packets_without_encounters=(),
        source_declared_encounters=(),
        source_declared_missing_db=(),
        source_declared_missing_packets=(),
    )

    prioritized = _review_backed_rows(audit)

    assert tuple(row.encounter_id for row, _gap in prioritized) == ("lokkestiiz",)
    assert prioritized[0][1].reconciled_facts == 2


def test_review_backed_rows_require_a_canonical_gap():
    complete = EncounterDatabaseCoverage(
        encounter_id="complete_boss",
        name="Complete Boss",
        npc_count=1,
        health_count=1,
        ability_count=8,
        mechanic_count=1,
        phase_count=1,
        dialogue_count=2,
        section_count=3,
        strategy_count=1,
        canonical_fact_count=2,
        canonical_evidence_count=2,
    )
    audit = EncounterContentGapAudit(
        content_id="trial",
        content_name="Trial",
        database_encounters=(complete,),
        packet_gaps=(_packet("complete_boss", facts=2),),
        encounters_without_packets=(),
        packets_without_encounters=(),
        source_declared_encounters=(),
        source_declared_missing_db=(),
        source_declared_missing_packets=(),
    )

    assert _review_backed_rows(audit) == ()
