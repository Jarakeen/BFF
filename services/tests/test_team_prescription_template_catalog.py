import json

import pytest

from services.team_prescription_template_catalog import (
    TemplateCatalogObjectiveEvaluator,
    TeamPrescriptionTemplateCatalog,
    catalog_candidates,
)


def _payload(
    *,
    duplicate: bool = False,
    schema_version: int = 1,
    complete_build: bool = False,
) -> dict:
    template = {
        "template_id": "btv:u50:warden-healer",
        "name": "Warden Healer Reference",
        "source_name": "BTV Tools",
        "source_url": "https://www.btvtools.com/roster-builder/guide",
        "retrieved_at": "2026-09-04",
        "base_score": 100.0,
        "slot_scores": {"Healer 1": 20.0},
        "goal_scores": {"Gryphon Heart": 5.0},
        "complete_build": complete_build,
        "unresolved": [
            "Reference source does not prove exact per-slot traits or enchants."
        ],
        "build": {
            "BuildName": "Warden Healer Reference",
            "EsoClass": "Warden",
            "Role": "Healer",
            "Mundus": "The Ritual",
            "FrontBarSkills": [
                "Combat Prayer",
                "Illustrious Healing",
                "Energy Orb",
                "Budding Seeds",
                "Radiating Regeneration",
                "Enchanted Forest",
            ],
        },
    }
    templates = [template]
    if duplicate:
        templates.append(dict(template))
    return {
        "schema_version": schema_version,
        "catalog_version": "u50-2026-09-04.1",
        "game_update": "U50",
        "templates": templates,
    }


def _write_catalog(tmp_path, payload: dict):
    path = tmp_path / "team_prescription_templates.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_catalog_loads_versioned_template_and_candidate_without_player_identity(tmp_path) -> None:
    snapshot = TeamPrescriptionTemplateCatalog(
        _write_catalog(tmp_path, _payload())
    ).load()

    assert snapshot.catalog_version == "u50-2026-09-04.1"
    assert snapshot.game_update == "U50"
    assert len(snapshot.templates) == 1
    candidate = catalog_candidates(snapshot)[0]
    assert candidate.candidate_id == "btv:u50:warden-healer"
    assert candidate.player_name is None
    assert candidate.candidate_build.Role == "Healer"
    assert candidate.candidate_build.EsoClass == "Warden"
    assert not candidate.has_complete_build_snapshot
    assert candidate.candidate_metadata["template_kind"] == "published_reference_template"
    assert candidate.candidate_metadata["observed_skills"][0] == "Combat Prayer"
    assert candidate.candidate_metadata["observed_mundus"] == "The Ritual"
    assert "BTV Tools" in candidate.candidate_source


def test_catalog_only_marks_candidate_complete_when_template_declares_it(tmp_path) -> None:
    snapshot = TeamPrescriptionTemplateCatalog(
        _write_catalog(tmp_path, _payload(complete_build=True))
    ).load()

    template = snapshot.templates[0]
    candidate = catalog_candidates(snapshot)[0]

    assert template.complete_build
    assert candidate.has_complete_build_snapshot


def test_template_objective_score_is_explicit_source_evidence_not_combat_math(tmp_path) -> None:
    snapshot = TeamPrescriptionTemplateCatalog(
        _write_catalog(tmp_path, _payload())
    ).load()
    candidate = catalog_candidates(snapshot)[0]

    result = TemplateCatalogObjectiveEvaluator(
        snapshot,
        goal="Gryphon Heart",
    )(candidate, "Healer 1")

    assert result.value == 125.0
    assert result.metric_name == "versioned reference-template score"
    assert result.constraints == ()
    assert result.is_rankable
    assert any("complete_build=false" in row for row in result.evidence)
    assert any("not canonical damage/HPS/tank math" in row for row in result.evidence)
    assert any("template limitation:" in row for row in result.evidence)


def test_catalog_rejects_duplicate_template_ids(tmp_path) -> None:
    with pytest.raises(ValueError, match="duplicate team prescription template_id"):
        TeamPrescriptionTemplateCatalog(
            _write_catalog(tmp_path, _payload(duplicate=True))
        ).load()


def test_catalog_rejects_unsupported_schema(tmp_path) -> None:
    with pytest.raises(ValueError, match="unsupported team prescription template catalog schema"):
        TeamPrescriptionTemplateCatalog(
            _write_catalog(tmp_path, _payload(schema_version=999))
        ).load()


def test_missing_catalog_is_explicit_empty_snapshot(tmp_path) -> None:
    snapshot = TeamPrescriptionTemplateCatalog(
        tmp_path / "does-not-exist.json"
    ).load()

    assert snapshot.templates == ()
    assert snapshot.catalog_version == "missing"
    assert snapshot.game_update == "unresolved"
