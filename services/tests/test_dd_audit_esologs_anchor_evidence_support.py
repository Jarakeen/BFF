from __future__ import annotations

import json

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from tools.dd_audit_esologs_anchor_evidence_support import (
    DDAuditEsoLogsAnchorEvidenceSupport,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(10.0, 1, RotationActionKind.SKILL, "Stampede", "back"),
            RotationAction(31.0, 1, RotationActionKind.SKILL, "Stampede", "back"),
            RotationAction(46.0, 1, RotationActionKind.SKILL, "Stampede", "back"),
        ),
    )


def _row(
    cast_seconds: float,
    impact_seconds: float,
    *,
    event_index: int,
    linked: bool = True,
) -> dict[str, object]:
    origin = 1_000_000.0
    return {
        "skill_entity_id": "stampede",
        "report_code": "REVIEWED-REPORT",
        "fight_id": 7,
        "source_id": 42,
        "cast_event_index": event_index,
        "cast_timestamp_ms": origin + cast_seconds * 1000.0,
        "cast_ability_id": 39807,
        "impact_event_index": event_index + 1,
        "impact_timestamp_ms": origin + impact_seconds * 1000.0,
        "impact_ability_id": 38792,
        "cast_track_id": event_index,
        "cast_track_linked": linked,
    }


def _write(tmp_path, rows) -> object:
    path = tmp_path / "stampede_anchors.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "replay_origin_timestamp_ms": 1_000_000.0,
                "observations": rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_maps_complete_exact_reviewed_observations_for_all_stampede_occurrences(tmp_path) -> None:
    path = _write(
        tmp_path,
        [
            _row(10.0, 10.173, event_index=100),
            _row(31.0, 31.201, event_index=200),
            _row(46.0, 46.119, event_index=300),
        ],
    )

    result = DDAuditEsoLogsAnchorEvidenceSupport().map_file(path, plan=_plan())

    assert result.unresolved == ()
    assert len(result.evidence) == 3
    assert tuple(row.action_time_seconds for row in result.evidence) == (10.0, 31.0, 46.0)
    assert tuple(row.action_sequence for row in result.evidence) == (1, 1, 1)
    assert tuple(row.anchor_time_seconds for row in result.evidence) == pytest.approx(
        (10.173, 31.201, 46.119)
    )
    assert all("REVIEWED-REPORT" in row.source for row in result.evidence)


def test_unlinked_observation_fails_closed_for_entire_observed_skill(tmp_path) -> None:
    path = _write(
        tmp_path,
        [
            _row(10.0, 10.173, event_index=100),
            _row(31.0, 31.201, event_index=200, linked=False),
            _row(46.0, 46.119, event_index=300),
        ],
    )

    result = DDAuditEsoLogsAnchorEvidenceSupport().map_file(path, plan=_plan())

    assert result.evidence == ()
    assert any("not cast-track-linked" in item for item in result.unresolved)
    assert any("covers 2 of 3" in item for item in result.unresolved)


def test_occurrence_count_mismatch_fails_closed_instead_of_returning_partial_evidence(tmp_path) -> None:
    path = _write(
        tmp_path,
        [
            _row(10.0, 10.173, event_index=100),
            _row(31.0, 31.201, event_index=200),
        ],
    )

    result = DDAuditEsoLogsAnchorEvidenceSupport().map_file(path, plan=_plan())

    assert result.evidence == ()
    assert any("covers 2 of 3" in item for item in result.unresolved)


def test_stale_cast_timestamp_does_not_nearest_match_plan_action(tmp_path) -> None:
    path = _write(
        tmp_path,
        [
            _row(10.01, 10.183, event_index=100),
            _row(31.0, 31.201, event_index=200),
            _row(46.0, 46.119, event_index=300),
        ],
    )

    result = DDAuditEsoLogsAnchorEvidenceSupport().map_file(path, plan=_plan())

    assert result.evidence == ()
    assert any("no exact stampede rotation action exists at 10.01s" in item for item in result.unresolved)
    assert any("covers 2 of 3" in item for item in result.unresolved)


def test_loader_rejects_non_boolean_cast_track_linkage(tmp_path) -> None:
    row = _row(10.0, 10.173, event_index=100)
    row["cast_track_linked"] = "yes"
    path = _write(tmp_path, [row])

    with pytest.raises(ValueError, match="cast_track_linked must be boolean"):
        DDAuditEsoLogsAnchorEvidenceSupport().load(path)
