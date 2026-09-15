from __future__ import annotations

from services.service_catalog import SERVICE_CATALOG


def test_actual_heal_attribute_projection_is_registered() -> None:
    descriptor = SERVICE_CATALOG.get("extreme.actual_heal_attribute_projection")

    assert descriptor is not None
    assert descriptor.domain == "extreme"
    assert descriptor.implementation_path == (
        "services.extreme_actual_heal_attribute_projection_service"
    )
    assert "extreme_actual_heal_attribute_denominator_projection" in descriptor.responsibilities
    assert descriptor.available is True


def test_actual_heal_armor_weight_legality_is_registered() -> None:
    descriptor = SERVICE_CATALOG.get("extreme.actual_heal_armor_weight_legality")

    assert descriptor is not None
    assert descriptor.domain == "extreme"
    assert descriptor.implementation_path == (
        "services.extreme_actual_heal_armor_weight_legality_service"
    )
    assert "extreme_actual_heal_armor_weight_legality" in descriptor.responsibilities
    assert descriptor.available is True


def test_actual_heal_armor_weight_frontier_is_registered() -> None:
    descriptor = SERVICE_CATALOG.get("extreme.actual_heal_armor_weight_frontier")

    assert descriptor is not None
    assert descriptor.domain == "extreme"
    assert descriptor.implementation_path == (
        "services.extreme_actual_heal_armor_weight_candidate_service"
    )
    assert descriptor.dependencies == ("extreme.actual_heal_armor_weight_legality",)
    assert "extreme_actual_heal_armor_weight_frontier" in descriptor.responsibilities
    assert descriptor.available is True


def test_actual_heal_armor_package_composition_is_registered() -> None:
    descriptor = SERVICE_CATALOG.get("extreme.actual_heal_armor_package_composition")

    assert descriptor is not None
    assert descriptor.domain == "extreme"
    assert descriptor.dependencies == ("extreme.actual_heal_armor_weight_frontier",)
    assert "extreme_actual_heal_gear_armor_weight_composition" in descriptor.responsibilities
    assert descriptor.available is True


def test_actual_heal_armor_progression_is_registered() -> None:
    descriptor = SERVICE_CATALOG.get("extreme.actual_heal_armor_progression")

    assert descriptor is not None
    assert descriptor.domain == "extreme"
    assert descriptor.implementation_path == (
        "services.extreme_actual_heal_armor_progression_service"
    )
    assert "extreme_actual_heal_armor_passive_progression" in descriptor.responsibilities
    assert descriptor.available is True
