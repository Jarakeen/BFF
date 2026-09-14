from __future__ import annotations

from engine.config import DEFAULT_DATABASE
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
    RotationTankTauntObligationService,
)


def test_pierce_armor_resolves_real_database_taunt_application() -> None:
    assert DEFAULT_DATABASE.is_file(), f"canonical ESO database is missing: {DEFAULT_DATABASE}"

    plan = RotationPlan(
        character_name="Database Tank",
        build_name="Taunt Integration",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Pierce Armor",
                bar="front",
            ),
        ),
    )
    requirement = RotationTankTauntApplicationRequirement(
        requirement_id="real_pierce_armor_taunt",
        source_skill_name="Pierce Armor",
        window_start_seconds=4.0,
        window_end_seconds=6.0,
        minimum_applications=1,
        bar="front",
        provenance=("canonical eso.db",),
    )

    result = RotationTankTauntObligationService(DEFAULT_DATABASE).assess(
        plan=plan,
        requirement=requirement,
    )

    assert result.resolved is True, result.unresolved
    assert result.satisfied is True
    assert result.unresolved == ()
    assert result.taunt_component_numbers
    assert len(result.applications) == 1
    assert result.applications[0].source_skill_name == "Pierce Armor"
    assert result.applications[0].time_seconds == 5.0
    assert result.applications[0].bar == "front"
    assert any("Pierce Armor coefficient" in item for item in result.evidence)


def test_real_database_taunt_identity_does_not_create_maintenance_semantics() -> None:
    """The integration gate proves application identity only, not taunt uptime."""

    plan = RotationPlan(
        character_name="Database Tank",
        build_name="Taunt Integration",
        duration_seconds=30.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Pierce Armor",
                bar="front",
            ),
        ),
    )
    requirement = RotationTankTauntApplicationRequirement(
        requirement_id="later_taunt_application",
        source_skill_name="Pierce Armor",
        window_start_seconds=20.0,
        window_end_seconds=25.0,
        minimum_applications=1,
    )

    result = RotationTankTauntObligationService(DEFAULT_DATABASE).assess(
        plan=plan,
        requirement=requirement,
    )

    assert result.resolved is True, result.unresolved
    assert result.satisfied is False
    assert result.applications == ()
    assert result.taunt_component_numbers
