from __future__ import annotations

import json
from pathlib import Path

from services.encounter_cleanse_method import (
    CleanseMethod,
    CleanseMethodResolution,
    EncounterCleanseMethodService,
)
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def _service(data_root: Path = ROOT / "data") -> EncounterService:
    return EncounterService(EncounterRepository.from_data_root(data_root))


def _write_synthetic_encounter(tmp_path: Path, evidence_rows: list[dict]) -> EncounterService:
    bosses = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    bosses.mkdir(parents=True)
    evidence.mkdir()
    (bosses / "x.json").write_text(
        json.dumps(
            {
                "id": "x",
                "mechanics": [
                    {
                        "name": "Debuff",
                        "description": "",
                        "requires_cleanse": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (evidence / "x.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "content_id": "fixture",
                "encounter_id": "x",
                "encounter_name": "Fixture",
                "evidence": evidence_rows,
            }
        ),
        encoding="utf-8",
    )
    return _service(tmp_path)


def test_real_oaxiltso_pool_is_encounter_interaction_without_claiming_skill_failure():
    rows = EncounterCleanseMethodService(_service()).methods("oaxiltso")

    assert len(rows) == 1
    row = rows[0]
    assert row.method == CleanseMethod.ENCOUNTER_INTERACTION
    assert row.resolution == CleanseMethodResolution.RESOLVED
    assert row.interaction == "cleanse_pool"
    assert row.distinct_sources == 3
    assert row.requires_player_build_capability is False
    assert row.player_skill_effectiveness_known is False


def test_real_hiath_purifying_light_uses_break_free_core_action():
    rows = EncounterCleanseMethodService(_service()).methods("hiath_the_battlemaster")

    assert len(rows) == 1
    row = rows[0]
    assert row.mechanic_name == "Purifying Light"
    assert row.method == CleanseMethod.CORE_ACTION
    assert row.resolution == CleanseMethodResolution.RESOLVED
    assert row.interaction == "break_free"
    assert row.distinct_sources == 1
    assert row.requires_player_build_capability is False
    assert row.player_skill_effectiveness_known is False


def test_real_xalvakka_soul_resonance_uses_corroborated_soul_purge_synergy():
    rows = EncounterCleanseMethodService(_service()).methods("xalvakka")

    assert len(rows) == 1
    row = rows[0]
    assert row.mechanic_name == "Soul Resonance"
    assert row.method == CleanseMethod.ENCOUNTER_INTERACTION
    assert row.resolution == CleanseMethodResolution.RESOLVED
    assert row.interaction == "soul_purge_synergy"
    assert row.reconciliation_status == "corroborated"
    assert row.distinct_sources == 3
    assert row.requires_player_build_capability is False
    assert row.player_skill_effectiveness_known is False


def test_explicit_group_skill_method_marks_build_capability_requirement(tmp_path):
    service = _write_synthetic_encounter(
        tmp_path,
        [
            {
                "fact_type": "cleanse_method",
                "fact_key": "debuff_cleanse_method",
                "value": {
                    "mechanic_name": "Debuff",
                    "method": "group_skill",
                    "interaction": "ally cleanse skill",
                    "player_skill_effectiveness_known": True,
                },
                "source_type": "uesp",
                "source_name": "Fixture Source",
                "source_locator": "Mechanic",
                "confidence": "high",
            }
        ],
    )

    row = EncounterCleanseMethodService(service).methods("x")[0]

    assert row.method == CleanseMethod.GROUP_SKILL
    assert row.requires_player_build_capability is True
    assert row.player_skill_effectiveness_known is True


def test_unknown_explicit_method_stays_unresolved(tmp_path):
    service = _write_synthetic_encounter(
        tmp_path,
        [
            {
                "fact_type": "cleanse_method",
                "fact_key": "debuff_cleanse_method",
                "value": {"mechanic_name": "Debuff", "method": "ritual_of_confusion"},
                "source_type": "uesp",
                "source_name": "Fixture Source",
                "source_locator": "Mechanic",
                "confidence": "high",
            }
        ],
    )

    row = EncounterCleanseMethodService(service).methods("x")[0]

    assert row.method is None
    assert row.resolution == CleanseMethodResolution.UNRESOLVED
    assert row.requires_player_build_capability is None


def test_conflicting_cleanse_method_evidence_never_selects_a_winner(tmp_path):
    service = _write_synthetic_encounter(
        tmp_path,
        [
            {
                "fact_type": "cleanse_method",
                "fact_key": "debuff_cleanse_method",
                "value": {"mechanic_name": "Debuff", "method": "self_skill"},
                "source_type": "uesp",
                "source_name": "Source A",
                "source_locator": "Mechanic",
                "confidence": "high",
            },
            {
                "fact_type": "cleanse_method",
                "fact_key": "debuff_cleanse_method",
                "value": {"mechanic_name": "Debuff", "method": "encounter_interaction"},
                "source_type": "guide",
                "source_name": "Source B",
                "source_locator": "Mechanic",
                "confidence": "high",
            },
        ],
    )

    row = EncounterCleanseMethodService(service).methods("x")[0]

    assert row.method is None
    assert row.resolution == CleanseMethodResolution.CONFLICTING
    assert row.requires_player_build_capability is None
