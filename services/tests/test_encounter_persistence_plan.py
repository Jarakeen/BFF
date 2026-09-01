from __future__ import annotations

from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence
from services.encounter_persistence_plan import build_persistence_plan
from services.encounter_promotion import classify_encounter_fact_for_promotion


def _candidate(rows):
    fact = reconcile_encounter_evidence(rows)[0]
    return classify_encounter_fact_for_promotion(fact)


def test_corroborated_fact_plans_one_canonical_row_and_all_evidence_rows():
    rows = [
        EncounterEvidence(
            encounter_id="taleria",
            fact_type="mechanic_state",
            fact_key="rapid_deluge_exists",
            value=True,
            source_type="uesp",
            source_name="UESP",
            source_revision="3582555",
            confidence="high",
        ),
        EncounterEvidence(
            encounter_id="taleria",
            fact_type="mechanic_state",
            fact_key="rapid_deluge_exists",
            value=True,
            source_type="guide",
            source_name="Nilandia",
            confidence="high",
        ),
        EncounterEvidence(
            encounter_id="taleria",
            fact_type="mechanic_state",
            fact_key="rapid_deluge_exists",
            value=True,
            source_type="combat_addon",
            source_name="Combat Alerts 2.6.2",
            confidence="high",
        ),
    ]

    plans = build_persistence_plan([_candidate(rows)])

    assert len(plans) == 1
    assert plans[0].fact.logical_ref == "mechanic_state:rapid_deluge_exists"
    assert plans[0].fact.canonical_kind == "mechanic_presence"
    assert plans[0].fact.payload_json == '{"name":"Rapid Deluge","present":true}'
    assert len(plans[0].evidence) == 3
    assert {row.source_type for row in plans[0].evidence} == {
        "uesp",
        "guide",
        "combat_addon",
    }


def test_single_source_fact_is_not_planned():
    row = EncounterEvidence(
        encounter_id="taleria",
        fact_type="mechanic_state",
        fact_key="winter_storm_exists",
        value=True,
        source_type="guide",
        source_name="Guide",
    )

    assert build_persistence_plan([_candidate([row])]) == []


def test_shared_update_and_patch_are_carried_to_canonical_fact():
    rows = [
        EncounterEvidence(
            encounter_id="taleria",
            fact_type="transition",
            fact_key="bridge_thresholds",
            value={"thresholds": ["50%", "35%", "20%"]},
            source_type="uesp",
            source_name="UESP",
            game_update="U51",
            patch_version="11.1.0",
        ),
        EncounterEvidence(
            encounter_id="taleria",
            fact_type="transition",
            fact_key="bridge_thresholds",
            value={"thresholds": ["50%", "35%", "20%"]},
            source_type="combat_addon",
            source_name="Combat Alerts",
            game_update="U51",
            patch_version="11.1.0",
        ),
    ]

    plan = build_persistence_plan([_candidate(rows)])[0]

    assert plan.fact.valid_from_update == "U51"
    assert plan.fact.valid_from_patch == "11.1.0"
