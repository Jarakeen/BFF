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
