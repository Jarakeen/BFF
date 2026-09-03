import json
import sqlite3

import pytest

from services.boss_encounter_projection import (
    project_boss_file,
    project_boss_payload,
    projection_to_packet,
    write_projection_packet,
)
from services.boss_encounter_projection_audit import audit_boss_encounter_projection
from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import PROMOTION_REVIEW_REQUIRED, build_encounter_promotion_preview


def _boss_payload():
    return {
        "id": "test_boss",
        "name": "Test Boss",
        "content_id": "test_trial",
        "abilities": [
            {"name": "Heavy Swing", "description": "A blockable hit.", "damage_type": "physical"},
            {"name": "Poison Pool", "description": "Drops poison.", "damage_type": "poison"},
        ],
        "mechanics": [
            {
                "name": "Poison Pool",
                "description": "Drops poison.",
                "mechanic_type": "targeted_hazard",
                "damage_type": "poison",
                "target_count": 2,
                "requires_movement": True,
                "requires_positioning": True,
                "requires_cleanse": True,
                "persistent_hazard": True,
                "interpretation_status": "inferred",
                "links": ["ignored for canonical payload"],
            }
        ],
        "phases": [{"name": "Execute", "starts_at_health_percent": 20}],
        "difficulty_notes": {"hardmode_info": ["Extra poison pools."]},
        "source": {
            "url": "https://example.invalid/Test_Boss",
            "page_title": "Online:Test Boss",
            "revision_id": 12345,
            "retrieved_at": "2026-09-03T00:00:00Z",
            "license": "CC BY-SA 2.5",
        },
    }


def test_projection_preserves_structured_mechanics_and_provenance(tmp_path):
    projection = project_boss_payload(_boss_payload(), source_path=tmp_path / "test_boss.json")

    assert projection.encounter_id == "test_boss"
    assert projection.content_id == "test_trial"
    assert projection.mechanic_count == 1
    assert projection.ability_count == 2
    assert projection.phase_count == 1
    assert projection.inferred_mechanic_count == 1
    assert projection.incomplete_mechanic_count == 0

    rows = {(row.fact_type, row.fact_key): row for row in projection.evidence}
    presence = rows[("mechanic_state", "poison_pool_exists")]
    detail = rows[("mechanic_detail", "poison_pool_detail")]
    ability = rows[("ability_detail", "heavy_swing")]

    assert presence.value is True
    assert detail.value["requires_cleanse"] is True
    assert "links" not in detail.value
    assert detail.confidence == "medium"
    assert detail.source_revision == "12345"
    assert detail.source_family == "uesp"
    assert "retrieved_at=2026-09-03T00:00:00Z" in detail.notes
    assert ability.value["damage_type"] == "physical"


def test_generated_uesp_evidence_remains_single_source_review_required():
    projection = project_boss_payload(_boss_payload())
    facts = reconcile_encounter_evidence(projection.evidence)
    candidates = build_encounter_promotion_preview(facts)

    assert facts
    assert all(fact.status == "single_source" for fact in facts)
    assert all(candidate.promotion_status == PROMOTION_REVIEW_REQUIRED for candidate in candidates)


def test_packet_output_is_deterministic_and_compatible(tmp_path):
    source = tmp_path / "test_boss.json"
    source.write_text(json.dumps(_boss_payload()), encoding="utf-8")
    projection = project_boss_file(source)
    target = tmp_path / "generated" / "test_boss.json"

    write_projection_packet(projection, target)
    first = target.read_text(encoding="utf-8")
    write_projection_packet(projection, target)
    second = target.read_text(encoding="utf-8")

    packet = projection_to_packet(projection)
    assert first == second
    assert packet["encounter_id"] == "test_boss"
    assert packet["evidence"][0]["source_family"] == "uesp"


def test_projection_requires_boss_identity():
    with pytest.raises(ValueError, match="no id"):
        project_boss_payload({"name": "Nameless Identity"})


def test_corpus_audit_reports_projection_and_database_coverage(tmp_path):
    source_dir = tmp_path / "bosses"
    source_dir.mkdir()
    (source_dir / "test_boss.json").write_text(json.dumps(_boss_payload()), encoding="utf-8")

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE encounter (id TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO encounter (id) VALUES ('test_boss')")
    try:
        result = audit_boss_encounter_projection(source_dir, connection=connection)
    finally:
        connection.close()

    assert result.source_files == 1
    assert result.projected_bosses == 1
    assert result.bosses_with_mechanics == 1
    assert result.mechanics == 1
    assert result.abilities == 2
    assert result.phases == 1
    assert result.inferred_mechanics == 1
    assert result.database_encounters_matched == 1
    assert result.database_encounters_missing == ()
    assert result.failures == ()
    assert result.review_required == result.reconciled_facts
