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


def test_generic_interruptible_flag_does_not_invent_bash_method(tmp_path):
    service = _write_synthetic(tmp_path, [])

    assert EncounterInterruptMethodService(service).methods("x") == ()


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
    assert row.requires_player_build_capability is False


def test_explicit_ranged_player_skill_marks_build_capability(tmp_path):
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

    row = EncounterInterruptMethodService(service).methods("x")[0]

    assert row.method == InterruptMethod.PLAYER_SKILL
    assert row.ranged_required is True
    assert row.requires_player_build_capability is True


def test_conflicting_interrupt_method_evidence_never_selects_winner(tmp_path):
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

    row = EncounterInterruptMethodService(service).methods("x")[0]

    assert row.method is None
    assert row.resolution == InterruptMethodResolution.CONFLICTING
    assert row.requires_player_build_capability is None
