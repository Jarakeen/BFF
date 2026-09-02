from pathlib import Path

from services.encounter_model_audit import audit_encounter_model
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService

ROOT = Path(__file__).resolve().parents[2]


def test_model_audit_reports_structured_phase9_domains_without_inference():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    audit = audit_encounter_model(service)
    by_id = {row.encounter_id: row for row in audit.rows}

    assert audit.encounter_count == len(service.encounter_ids())
    assert audit.encounter_count > 0
    assert all(row.boss_actor_count == 1 for row in audit.rows)

    oaxiltso = by_id["oaxiltso"]
    assert oaxiltso.mechanic_count > 0
    assert oaxiltso.requirement_count > 0
    assert oaxiltso.positioning_constraint_count > 0
    assert oaxiltso.target_constraint_count > 0
    assert oaxiltso.transition_fact_count > 0
    assert oaxiltso.add_group_fact_count == 0
    assert oaxiltso.damage_window_fact_count == 0

    taleria = by_id["tideborn_taleria"]
    assert taleria.temporal_evidence_count > 0
    assert taleria.transition_fact_count > 0
    assert taleria.evidence_fact_count > 0

    archcustodian = by_id["archcustodian"]
    assert archcustodian.add_group_fact_count == 1
    assert archcustodian.damage_window_fact_count == 1
    assert archcustodian.evidence_fact_count == 2

    assert audit.encounters_with_mechanics > 0
    assert audit.encounters_with_requirements > 0
    assert audit.encounters_with_positioning_constraints > 0
    assert audit.encounters_with_temporal_evidence > 0
    assert audit.encounters_with_transition_evidence > 0
    assert audit.encounters_with_target_constraints > 0
    assert audit.encounters_with_evidence > 0
    assert audit.encounters_with_add_group_evidence > 0
    assert audit.encounters_with_damage_window_evidence > 0


def test_model_audit_counts_explicit_add_group_and_damage_window_facts(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text(
        '{"id":"x","mechanics":['
        '{"name":"Stack","description":"","requires_positioning":true,"target_count":2}'
        ']}'
    )
    (evidence / "x.json").write_text(
        '{"encounter_id":"x","evidence":['
        '{"fact_type":"add_group","fact_key":"adds",'
        '"value":{"count":2},"source_type":"guide","source_name":"A"},'
        '{"fact_type":"damage_window","fact_key":"shield",'
        '"value":{"damageable":false},"source_type":"guide","source_name":"A"}'
        ']}'
    )
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))

    audit = audit_encounter_model(service)
    row = audit.rows[0]

    assert row.boss_actor_count == 1
    assert row.positioning_constraint_count == 1
    assert row.target_constraint_count == 1
    assert row.add_group_fact_count == 1
    assert row.damage_window_fact_count == 1
    assert audit.encounters_with_add_group_evidence == 1
    assert audit.encounters_with_damage_window_evidence == 1
