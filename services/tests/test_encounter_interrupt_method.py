from __future__ import annotations

import json
from pathlib import Path

from services.encounter_interrupt_method import (
    EncounterInterruptMethodService,
    InterruptMethod,
    InterruptMethodResolution,
)
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService
from services.eso_combat_rules import STANDARD_INTERRUPT


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
                        "name": "Cast",
                        "description": "",
                        "interruptible": True,
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


def test_generic_interruptible_flag_uses_sourced_global_bash_rule(tmp_path):
    service = _write_synthetic(tmp_path, [])

    row = EncounterInterruptMethodService(service).methods("x")[0]

    assert row.method == InterruptMethod.CORE_BASH
    assert row.resolution == InterruptMethodResolution.RESOLVED
    assert row.interaction == "standard_interrupt_bash"
    assert row.fact_id == f"global_rule:{STANDARD_INTERRUPT.rule_id}"
    assert row.reconciliation_status == "global_rule"
    assert row.ranged_required is False
    assert row.rule_source_name == STANDARD_INTERRUPT.source_name
    assert row.rule_source_url == STANDARD_INTERRUPT.source_url
    assert row.requires_player_build_capability is False


def test_explicit_core_bash_method_resolves_without_build_requirement(tmp_path):
    service = _write_synthetic(
        tmp_path,
        [
            {
                "fact_type": "interrupt_method",
                "fact_key": "cast_interrupt_method",
                "value": {
                    "mechanic_name": "Cast",
                    "method": "core_bash",
                    "interaction": "bash",
                    "ranged_required": False,
                },
                "source_type": "uesp",
                "source_name": "Fixture Source",
                "source_locator": "Mechanic",
                "confidence": "high",
            }
        ],
    )

    row = EncounterInterruptMethodService(service).methods("x")[0]

    assert row.method == InterruptMethod.CORE_BASH
    assert row.resolution == InterruptMethodResolution.RESOLVED
    assert row.interaction == "bash"
    assert row.ranged_required is False
    assert row.reconciliation_status == "single_source"
    assert row.requires_player_build_capability is False


def test_explicit_ranged_player_skill_overrides_global_bash_rule(tmp_path):
    service = _write_synthetic(
        tmp_path,
        [
            {
                "fact_type": "interrupt_method",
                "fact_key": "cast_interrupt_method",
                "value": {
                    "mechanic_name": "Cast",
                    "method": "player_skill",
                    "interaction": "ranged_interrupt",
                    "ranged_required": True,
                },
                "source_type": "uesp",
                "source_name": "Fixture Source",
                "source_locator": "Mechanic",
                "confidence": "high",
            }
        ],
    )

    rows = EncounterInterruptMethodService(service).methods("x")

    assert len(rows) == 1
    row = rows[0]
    assert row.method == InterruptMethod.PLAYER_SKILL
    assert row.ranged_required is True
    assert row.requires_player_build_capability is True
    assert row.reconciliation_status == "single_source"


def test_conflicting_interrupt_method_evidence_blocks_global_fallback(tmp_path):
    service = _write_synthetic(
        tmp_path,
        [
            {
                "fact_type": "interrupt_method",
                "fact_key": "cast_interrupt_method",
                "value": {"mechanic_name": "Cast", "method": "core_bash"},
                "source_type": "uesp",
                "source_name": "Source A",
                "source_locator": "Mechanic",
                "confidence": "high",
            },
            {
                "fact_type": "interrupt_method",
                "fact_key": "cast_interrupt_method",
                "value": {"mechanic_name": "Cast", "method": "player_skill"},
                "source_type": "guide",
                "source_name": "Source B",
                "source_locator": "Mechanic",
                "confidence": "high",
            },
        ],
    )

    rows = EncounterInterruptMethodService(service).methods("x")

    assert len(rows) == 1
    row = rows[0]
    assert row.method is None
    assert row.resolution == InterruptMethodResolution.CONFLICTING
    assert row.requires_player_build_capability is None
