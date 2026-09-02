from pathlib import Path

from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService

ROOT = Path(__file__).resolve().parents[2]


def test_archcustodian_exposes_source_backed_damage_window_and_add_group():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    windows = service.damage_window_evidence("archcustodian")
    assert len(windows) == 1
    window = windows[0]
    assert window.fact_key == "vaporization_protocol_shield_cycle"
    assert window.status == "single_source"
    assert window.value["shield_active"] == {
        "damageable": False,
        "state": "invulnerable",
    }
    assert window.value["shield_removed"] == {
        "damageable": True,
        "state": "burn_phase",
    }
    assert window.value["cycle_repeats"] is True

    add_groups = service.add_group_evidence("archcustodian")
    assert len(add_groups) == 1
    add_group = add_groups[0]
    assert add_group.fact_key == "post_burn_factotums"
    assert add_group.status == "single_source"
    assert add_group.value == {
        "members": ["Calefactors", "Dissectors"],
        "trigger": "after_burn_phase",
    }


def test_archcustodian_evidence_remains_source_qualified_not_canonicalized():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    window = service.damage_window_evidence("archcustodian")[0]
    add_group = service.add_group_evidence("archcustodian")[0]

    assert window.distinct_sources == 1
    assert add_group.distinct_sources == 1
    assert window.status == "single_source"
    assert add_group.status == "single_source"
