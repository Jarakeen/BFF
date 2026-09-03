from pathlib import Path

import pytest

from minmax.dd_damage import DDDamageEvent
from minmax.resource_costs import ResourceType
from tools.audit_phase12_saved_dd_candidates import (
    _parser,
    audit_saved_dd_candidates,
)


def test_saved_dd_audit_requires_explicit_build_name() -> None:
    with pytest.raises(SystemExit):
        _parser().parse_args([])


def test_saved_dd_audit_parser_preserves_explicit_event_inputs() -> None:
    args = _parser().parse_args(
        [
            "--build",
            "My DD",
            "--active-bar",
            "back",
            "--resource",
            "stamina",
            "--base-value",
            "1500",
            "--scaling-coefficient",
            "1.25",
            "--damage-type",
            "physical",
            "--target-resistance",
            "18200",
        ]
    )

    assert args.build == "My DD"
    assert args.active_bar == "back"
    assert args.resource == "stamina"
    assert args.base_value == 1500.0
    assert args.scaling_coefficient == 1.25
    assert args.damage_type == "physical"
    assert args.target_resistance == 18_200.0


def test_saved_dd_audit_fails_clearly_when_database_is_missing(tmp_path: Path) -> None:
    result = audit_saved_dd_candidates(
        database_path=tmp_path / "missing.db",
        builds_path=tmp_path / "missing-builds.json",
        build_name="My DD",
        active_bar="front",
        resource=ResourceType.MAGICKA,
        duration_seconds=20.0,
        event=DDDamageEvent(base_value=1000.0),
        target_resistance=18_200.0,
    )

    assert result == 1
