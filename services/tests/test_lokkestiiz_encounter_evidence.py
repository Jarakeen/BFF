from pathlib import Path

from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService

ROOT = Path(__file__).resolve().parents[2]


def test_lokkestiiz_exposes_source_backed_flight_damage_window():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    windows = service.damage_window_evidence("lokkestiiz")

    assert len(windows) == 1
    window = windows[0]
    assert window.fact_key == "aerial_onslaught_flight"
    assert window.status == "single_source"
    assert window.value["trigger_health_percent"] == [80, 50, 20]
    assert window.value["boss_targetable"] is False
    assert window.value["boss_damageable"] is False
    assert window.value["state"] == "boss_airborne"
    assert window.value["adds_active"] is True
    assert window.value["raid_damage_active"] is True
    assert window.value["final_beam_requires_block"] is True


def test_lokkestiiz_flight_is_boss_downtime_but_not_raid_action_downtime():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    window = service.damage_window_evidence("lokkestiiz")[0]

    assert window.value["boss_damageable"] is False
    assert window.value["adds_active"] is True
    assert window.value["raid_damage_active"] is True
    assert window.value["flight_attacks"] == [
        "lightning_strafe_with_lingering_damage",
        "ice_and_shock_sweeping_beam",
    ]


def test_lokkestiiz_exposes_atronach_add_group_without_inventing_exact_count():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    groups = service.add_group_evidence("lokkestiiz")

    assert len(groups) == 1
    group = groups[0]
    assert group.fact_key == "aerial_onslaught_atronachs"
    assert group.status == "single_source"
    assert group.value == {
        "members": ["Frost Atronach", "Storm Atronach"],
        "trigger": "aerial_onslaught_flight",
        "exact_count_resolved": False,
    }


def test_lokkestiiz_evidence_remains_source_qualified_not_canonicalized():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    window = service.damage_window_evidence("lokkestiiz")[0]
    group = service.add_group_evidence("lokkestiiz")[0]

    assert window.distinct_sources == 1
    assert group.distinct_sources == 1
    assert window.status == "single_source"
    assert group.status == "single_source"
