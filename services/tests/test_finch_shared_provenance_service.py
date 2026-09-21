from __future__ import annotations

from pathlib import Path

from services.finch_api_client import FinchSharedSnapshot
from services.finch_shared_provenance_service import (
    FinchSharedProvenanceService,
    format_shared_timestamp,
)


def _snapshot(updated_at: str) -> FinchSharedSnapshot:
    return FinchSharedSnapshot(
        kind="raid_plan",
        snapshot_key="rg-pm",
        schema_version=3,
        payload={"plan_id": "rg-pm"},
        published_by="BFF",
        updated_at=updated_at,
    )


def test_provenance_reports_not_copied_before_receipt_exists(tmp_path) -> None:
    service = FinchSharedProvenanceService(tmp_path / "provenance.json")

    assert service.relation_for(
        _snapshot("2026-09-21T01:00:00+00:00")
    ) == "Not copied locally"


def test_provenance_records_exact_snapshot_used_for_local_copy(tmp_path) -> None:
    service = FinchSharedProvenanceService(tmp_path / "provenance.json")
    snapshot = _snapshot("2026-09-21T01:00:00+00:00")

    row = service.record_copy(snapshot=snapshot, local_key="rg-pm-shared-copy")

    assert row.snapshot_key == "rg-pm"
    assert row.local_key == "rg-pm-shared-copy"
    assert row.published_by == "BFF"
    assert row.source_updated_at == "2026-09-21T01:00:00+00:00"
    assert (
        service.relation_for(snapshot)
        == "Copied from this Finch snapshot • local: rg-pm-shared-copy"
    )


def test_provenance_detects_remote_change_since_copy(tmp_path) -> None:
    service = FinchSharedProvenanceService(tmp_path / "provenance.json")
    service.record_copy(
        snapshot=_snapshot("2026-09-21T01:00:00+00:00"),
        local_key="rg-pm-shared-copy",
    )

    relation = service.relation_for(
        _snapshot("2026-09-21T02:00:00+00:00")
    )

    assert relation == (
        "Updated on Finch since copy • local: rg-pm-shared-copy"
    )


def test_provenance_does_not_claim_local_edit_freshness(tmp_path) -> None:
    service = FinchSharedProvenanceService(tmp_path / "provenance.json")
    service.record_copy(
        snapshot=_snapshot("2026-09-21T02:00:00+00:00"),
        local_key="rg-pm-shared-copy",
    )

    relation = service.relation_for(
        _snapshot("2026-09-21T01:00:00+00:00")
    )

    assert relation == (
        "Local copy came from a newer Finch snapshot • rg-pm-shared-copy"
    )


def test_shared_timestamp_formats_utc_consistently() -> None:
    assert (
        format_shared_timestamp("2026-09-20T22:15:00-04:00")
        == "2026-09-21 02:15 UTC"
    )
    assert format_shared_timestamp("") == "Unknown time"
