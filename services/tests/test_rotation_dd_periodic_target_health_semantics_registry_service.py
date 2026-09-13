import json

import pytest

from services.rotation_dd_periodic_target_health_semantics_registry_service import (
    RotationDDPeriodicTargetHealthSemanticsRegistryService,
)
from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
)


def _write(tmp_path, payload):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_missing_registry_resolves_to_no_semantics(tmp_path) -> None:
    service = RotationDDPeriodicTargetHealthSemanticsRegistryService(
        tmp_path / "missing.json"
    )

    assert service.load() == ()


def test_empty_registry_resolves_to_no_semantics(tmp_path) -> None:
    path = _write(tmp_path, {"schema_version": 1, "entries": []})

    assert RotationDDPeriodicTargetHealthSemanticsRegistryService(path).load() == ()


def test_registry_loads_reviewed_semantic(tmp_path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "entries": [
                {
                    "skill_entity_id": "Reviewed Dot",
                    "coefficient_number": 2,
                    "policy": "dynamic_at_tick",
                    "source": "reviewed combat-log evidence",
                }
            ],
        },
    )

    rows = RotationDDPeriodicTargetHealthSemanticsRegistryService(path).load()

    assert len(rows) == 1
    assert rows[0].skill_entity_id == "reviewed_dot"
    assert rows[0].coefficient_number == 2
    assert rows[0].policy is PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK
    assert rows[0].source == "reviewed combat-log evidence"


def test_duplicate_skill_component_is_rejected(tmp_path) -> None:
    row = {
        "skill_entity_id": "Reviewed Dot",
        "coefficient_number": 1,
        "policy": "snapshot_at_cast",
        "source": "reviewed source",
    }
    path = _write(
        tmp_path,
        {"schema_version": 1, "entries": [row, dict(row)]},
    )

    with pytest.raises(ValueError, match="duplicate DD periodic target-Health semantics"):
        RotationDDPeriodicTargetHealthSemanticsRegistryService(path).load()


def test_invalid_schema_version_is_rejected(tmp_path) -> None:
    path = _write(tmp_path, {"schema_version": 2, "entries": []})

    with pytest.raises(ValueError, match="schema_version must be 1"):
        RotationDDPeriodicTargetHealthSemanticsRegistryService(path).load()
