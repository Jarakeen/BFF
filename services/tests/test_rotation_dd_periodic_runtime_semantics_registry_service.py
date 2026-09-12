import json

import pytest

from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageMagnitudePolicy,
    PeriodicDamageRefreshBoundary,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)


def test_missing_registry_is_reviewed_empty(tmp_path) -> None:
    service = RotationDDPeriodicRuntimeSemanticsRegistryService(
        tmp_path / "missing.json"
    )
    assert service.load() == ()


def test_registry_loads_explicit_runtime_and_magnitude_semantics(tmp_path) -> None:
    path = tmp_path / "dd_periodic.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "burning_talons",
                        "coefficient_number": 2,
                        "first_tick_offset_seconds": 2.0,
                        "refresh_boundary": "replace_before_recast_tick",
                        "activation_anchor": "impact",
                        "magnitude_policy": "snapshot_at_cast",
                        "successive_hit_multiplier": 1.15,
                        "source": "reviewed U50 combat evidence",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rows = RotationDDPeriodicRuntimeSemanticsRegistryService(path).load()

    assert len(rows) == 1
    row = rows[0]
    assert row.skill_entity_id == "burning_talons"
    assert row.coefficient_number == 2
    assert row.refresh_boundary is PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK
    assert row.activation_anchor is PeriodicDamageActivationAnchor.IMPACT
    assert row.magnitude_policy is PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST
    assert row.successive_hit_multiplier == 1.15
    assert row.source == "reviewed U50 combat evidence"


def test_registry_defaults_legacy_entries_to_cast_anchor(tmp_path) -> None:
    path = tmp_path / "dd_periodic.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "burning_talons",
                        "coefficient_number": 2,
                        "first_tick_offset_seconds": 2.0,
                        "refresh_boundary": "replace_before_recast_tick",
                        "magnitude_policy": "snapshot_at_cast",
                        "source": "reviewed U50 combat evidence",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    row = RotationDDPeriodicRuntimeSemanticsRegistryService(path).load()[0]

    assert row.activation_anchor is PeriodicDamageActivationAnchor.CAST


def test_registry_rejects_duplicate_component_semantics(tmp_path) -> None:
    path = tmp_path / "dd_periodic.json"
    entry = {
        "skill_entity_id": "burning_talons",
        "coefficient_number": 2,
        "first_tick_offset_seconds": 2.0,
        "refresh_boundary": "replace_before_recast_tick",
        "magnitude_policy": "snapshot_at_cast",
        "source": "reviewed U50 combat evidence",
    }
    path.write_text(
        json.dumps({"schema_version": 1, "entries": [entry, entry]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate DD periodic runtime semantics"):
        RotationDDPeriodicRuntimeSemanticsRegistryService(path).load()


def test_registry_requires_explicit_magnitude_policy(tmp_path) -> None:
    path = tmp_path / "dd_periodic.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "burning_talons",
                        "coefficient_number": 2,
                        "first_tick_offset_seconds": 2.0,
                        "refresh_boundary": "replace_before_recast_tick",
                        "source": "reviewed U50 combat evidence",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="magnitude_policy"):
        RotationDDPeriodicRuntimeSemanticsRegistryService(path).load()


def test_registry_rejects_nonpositive_successive_hit_multiplier(tmp_path) -> None:
    path = tmp_path / "dd_periodic.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "skill_entity_id": "skeletal_archer",
                        "coefficient_number": 1,
                        "first_tick_offset_seconds": 2.0,
                        "refresh_boundary": "replace_before_recast_tick",
                        "magnitude_policy": "dynamic_at_tick",
                        "successive_hit_multiplier": 0.0,
                        "source": "reviewed combat evidence",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="successive_hit_multiplier"):
        RotationDDPeriodicRuntimeSemanticsRegistryService(path).load()
