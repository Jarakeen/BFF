from __future__ import annotations

import pytest

from services.extreme_record_objective_catalog_service import (
    EXTREME_RECORD_OBJECTIVES,
    ExtremeRecordDomain,
    ExtremeRecordMeasure,
    get_extreme_record_objective,
    list_extreme_record_objectives,
)


def test_extreme_record_objective_keys_are_unique_and_stable():
    keys = [objective.key for objective in EXTREME_RECORD_OBJECTIVES]

    assert len(keys) == len(set(keys))
    assert {
        "actual_heal",
        "critical_heal",
        "healing_done",
        "critical_healing",
        "max_health",
        "max_magicka",
        "max_stamina",
        "weapon_damage",
        "spell_damage",
        "weapon_critical",
        "spell_critical",
        "critical_damage",
        "physical_penetration",
        "spell_penetration",
        "physical_resistance",
        "spell_resistance",
        "damage_shield",
        "block_mitigation",
        "block_cost_reduction",
        "bash_damage",
        "health_recovery",
        "magicka_recovery",
        "stamina_recovery",
        "resource_sustain",
        "ultimate_generation",
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
        "invisibility_duration",
        "invisibility_uptime",
    }.issubset(set(keys))


def test_event_healing_records_require_runtime_proof():
    actual = get_extreme_record_objective("actual_heal")
    critical = get_extreme_record_objective("critical_heal")

    assert actual.domain is ExtremeRecordDomain.HEALING
    assert actual.measure is ExtremeRecordMeasure.EVENT
    assert actual.runtime_required
    assert critical.domain is ExtremeRecordDomain.HEALING
    assert critical.measure is ExtremeRecordMeasure.EVENT
    assert critical.runtime_required


def test_raw_cap_sensitive_records_report_effective_value_separately():
    for key in (
        "physical_resistance",
        "spell_resistance",
        "physical_penetration",
        "spell_penetration",
        "critical_damage",
        "critical_healing",
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
    ):
        assert get_extreme_record_objective(key).report_effective_cap


def test_stealth_records_separate_detection_duration_and_sustained_uptime():
    stealth = list_extreme_record_objectives(domain="stealth")

    assert [objective.key for objective in stealth] == [
        "detection_radius_reduction",
        "invisibility_duration",
        "invisibility_uptime",
    ]
    assert stealth[0].measure is ExtremeRecordMeasure.SNAPSHOT
    assert stealth[1].measure is ExtremeRecordMeasure.DURATION
    assert stealth[2].measure is ExtremeRecordMeasure.SUSTAINED


def test_domain_filter_accepts_enum_and_string():
    assert list_extreme_record_objectives(domain=ExtremeRecordDomain.MOVEMENT) == (
        *list_extreme_record_objectives(domain="movement"),
    )


def test_unknown_objective_and_domain_fail_closed():
    with pytest.raises(ValueError, match="Unsupported Extreme Records objective"):
        get_extreme_record_objective("make_me_a_god")

    with pytest.raises(ValueError, match="Unsupported Extreme Records domain"):
        list_extreme_record_objectives(domain="nonsense")
