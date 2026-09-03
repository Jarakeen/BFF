from __future__ import annotations

import json
from pathlib import Path

from services.encounter_execution_method import (
    EncounterExecutionMethodService,
    ExecutionMethod,
    ExecutionMethodResolution,
)
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def _service(data_root: Path) -> EncounterService:
    return EncounterService(EncounterRepository.from_data_root(data_root))


def _write_synthetic(tmp_path: Path, evidence_rows: list[dict]) -> EncounterService:
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
                        "name": "Charge",
                        "description": "",
                        "requires_movement": True,
                        "requires_positioning": True,
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


def test_explicit_execution_method_resolves_exact_requirement(tmp_path):
    service = _write_synthetic(
        tmp_path,
        [
            {
                "fact_type": "execution_method",
                "fact_key": "charge_movement",
                "value": {
                    "mechanic_name": "Charge",
                    "requirement_type": "movement",
                    "method": "dodge",
                },
                "source_type": "uesp",
                "source_name": "Fixture Source",
                "source_locator": "Charge",
                "confidence": "high",
            }
        ],
    )

    rows = EncounterExecutionMethodService(service).methods("x")

    assert len(rows) == 1
    assert rows[0].mechanic_name == "Charge"
    assert rows[0].requirement_type == "movement"
    assert rows[0].method == ExecutionMethod.DODGE
    assert rows[0].resolution == ExecutionMethodResolution.RESOLVED


def test_conflicting_explicit_execution_evidence_blocks_legacy_fallback(tmp_path):
    service = _write_synthetic(
        tmp_path,
        [
            {
                "fact_type": "execution_method",
                "fact_key": "charge_movement",
                "value": {
                    "mechanic_name": "Charge",
                    "requirement_type": "movement",
                    "method": "dodge",
                },
                "source_type": "uesp",
                "source_name": "Source A",
                "source_locator": "Charge",
                "confidence": "high",
            },
            {
                "fact_type": "execution_method",
                "fact_key": "charge_movement",
                "value": {
                    "mechanic_name": "Charge",
                    "requirement_type": "movement",
                    "method": "avoid_hazard",
                },
                "source_type": "guide",
                "source_name": "Source B",
                "source_locator": "Charge",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic_detail",
                "fact_key": "savage_blitz_targeting",
                "value": {
                    "targets_farthest_player": True,
                    "avoidable_by_dodge": True,
                },
                "source_type": "uesp",
                "source_name": "Legacy Source",
                "source_locator": "Charge",
                "confidence": "high",
            },
        ],
    )

    rows = EncounterExecutionMethodService(service).methods("x")

    assert len(rows) == 1
    assert rows[0].resolution == ExecutionMethodResolution.CONFLICTING
    assert rows[0].method is None
    assert rows[0].requirement_type == ""


def test_real_oaxiltso_legacy_structured_facts_resolve_current_execution_methods():
    service = _service(ROOT / "data")
    rows = EncounterExecutionMethodService(service).methods("oaxiltso")
    by_key = {(row.mechanic_name, row.requirement_type): row for row in rows}

    expected = {
        ("Savage Blitz", "movement"): ExecutionMethod.DODGE,
        ("Savage Blitz", "positioning"): ExecutionMethod.BAIT_FARTHEST,
        ("Blistering Smash", "positioning"): ExecutionMethod.AVOID_HAZARD,
        ("Noxious Sludge", "movement"): ExecutionMethod.MOVE_TO_INTERACTION,
        ("Noxious Sludge", "positioning"): ExecutionMethod.HAZARD_DROP_MANAGEMENT,
        ("Summon Havocrel Annihilators", "positioning"): ExecutionMethod.SEPARATE_ADD_FROM_BOSS,
    }

    assert set(by_key) == set(expected)
    for key, method in expected.items():
        assert by_key[key].method == method
        assert by_key[key].resolution == ExecutionMethodResolution.RESOLVED
