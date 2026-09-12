import json

import pytest

from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


def test_review_ledger_loads_partial_evidence_without_promoting_completion(tmp_path) -> None:
    path = tmp_path / "review.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "skeletal_archer",
                        "coefficient_number": 1,
                        "duration_seconds": 20.0,
                        "reviewed_interval_seconds": 2.0,
                        "activation_anchor": None,
                        "first_tick_offset_seconds": None,
                        "refresh_boundary": None,
                        "magnitude_policy": None,
                        "successive_hit_multiplier": 1.15,
                        "evidence": ["reviewed tooltip evidence"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = RotationDDPeriodicRuntimeSemanticsReviewService(path).load()

    assert len(rows) == 1
    row = rows[0]
    assert row.skill_entity_id == "skeletal_archer"
    assert row.reviewed_interval_seconds == 2.0
    assert row.successive_hit_multiplier == 1.15
    assert row.executable_complete is False
    assert row.unresolved_executable_fields == (
        "activation_anchor",
        "first_tick_offset_seconds",
        "refresh_boundary",
        "magnitude_policy",
    )


def test_repository_review_ledger_tracks_the_seven_current_dd_components() -> None:
    rows = RotationDDPeriodicRuntimeSemanticsReviewService().load()

    assert {(row.skill_entity_id, row.coefficient_number) for row in rows} == {
        ("unnerving_boneyard", 1),
        ("detonating_siphon", 1),
        ("flawless_dawnbreaker", 2),
        ("skeletal_archer", 1),
        ("scalding_rune", 2),
        ("stampede", 2),
        ("meteor", 2),
    }
    assert all(row.executable_complete is False for row in rows)

    by_key = {(row.skill_entity_id, row.coefficient_number): row for row in rows}
    assert by_key[("skeletal_archer", 1)].reviewed_interval_seconds == 2.0
    assert by_key[("skeletal_archer", 1)].successive_hit_multiplier == 1.15
    stampede = by_key[("stampede", 2)]
    assert stampede.reviewed_interval_seconds == 1.0
    assert stampede.activation_anchor == "impact"
    assert stampede.first_tick_offset_seconds == 1.0
    assert stampede.unresolved_executable_fields == (
        "refresh_boundary",
        "magnitude_policy",
    )
    assert by_key[("meteor", 2)].reviewed_interval_seconds == 1.0


def test_review_ledger_rejects_duplicate_component_rows(tmp_path) -> None:
    path = tmp_path / "review.json"
    entry = {
        "skill_entity_id": "stampede",
        "coefficient_number": 2,
        "evidence": ["reviewed evidence"],
    }
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [entry, entry]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate DD periodic semantics review"):
        RotationDDPeriodicRuntimeSemanticsReviewService(path).load()


def test_review_ledger_requires_evidence_provenance(tmp_path) -> None:
    path = tmp_path / "review.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "stampede",
                        "coefficient_number": 2,
                        "evidence": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires evidence provenance"):
        RotationDDPeriodicRuntimeSemanticsReviewService(path).load()


def test_review_ledger_rejects_unknown_activation_anchor(tmp_path) -> None:
    path = tmp_path / "review.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "stampede",
                        "coefficient_number": 2,
                        "activation_anchor": "moon_phase",
                        "evidence": ["deliberately invalid test evidence"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="activation_anchor"):
        RotationDDPeriodicRuntimeSemanticsReviewService(path).load()
