from minmax.skill_component_runtime_timing import RuntimeCadenceBoundKind
from services.rotation_healer_u50_periodic_cadence_repository import (
    RotationHealerU50PeriodicCadenceRepository,
)


def test_illustrious_healing_has_reviewed_one_second_static_hot_cadence():
    result = RotationHealerU50PeriodicCadenceRepository().get(
        source_name="Illustrious Healing",
        coefficient_number=1,
    )

    assert result is not None
    assert result.timing.interval_seconds == 1.0
    assert result.timing.bound_kind is RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW
    assert result.timing.source == "reviewed_zos_update35_final"
    assert any("v8.1.5" in item for item in result.provenance)
    assert any("static-based" in item for item in result.provenance)


def test_radiating_regeneration_has_reviewed_two_second_target_hot_cadence():
    result = RotationHealerU50PeriodicCadenceRepository().get(
        source_name="Radiating Regeneration",
        coefficient_number=1,
    )

    assert result is not None
    assert result.timing.interval_seconds == 2.0
    assert result.timing.bound_kind is RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW
    assert result.timing.source == "reviewed_zos_update35_final"
    assert any("target-based" in item for item in result.provenance)


def test_echoing_vigor_has_reviewed_two_second_target_hot_cadence():
    result = RotationHealerU50PeriodicCadenceRepository().get(
        source_name="Echoing Vigor",
        coefficient_number=1,
    )

    assert result is not None
    assert result.timing.interval_seconds == 2.0
    assert result.timing.bound_kind is RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW
    assert result.timing.source == "reviewed_zos_update35_final"
    assert any("target-based" in item for item in result.provenance)


def test_repository_is_case_insensitive_but_coefficient_specific():
    repository = RotationHealerU50PeriodicCadenceRepository()

    assert repository.get(source_name="illustrious healing", coefficient_number=1) is not None
    assert repository.get(source_name="RADIATING REGENERATION", coefficient_number=1) is not None
    assert repository.get(source_name="ILLUSTRIOUS HEALING", coefficient_number=2) is None
