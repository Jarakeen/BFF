from pathlib import Path
import sqlite3

from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    SEVENTH_LEGION_BRUTE_POWER_CONDITION,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitness,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    ExtremeActualHealSetupActionWitness,
)


class _NoGearPreconditions:
    @staticmethod
    def resolve(build, *, active_bar="front"):
        return ExtremeActualHealGearPreconditionWitness()


class _ResolveLegality:
    @staticmethod
    def witness(capability, context):
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Vigor",
            skill_line="Assault",
            ability_id=12345,
            evidence="Vigor grants Resolve",
        )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
    return path


def _build(*, vigor_on_back: bool) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Seventh Legion Brute"
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = [
        "Vigor" if vigor_on_back else "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Back Ultimate",
    ]
    return build


def test_seventh_legion_condition_requires_resolve_witness_on_inactive_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_ResolveLegality(),
    )

    active = service.resolve(_build(vigor_on_back=True), active_bar="front")
    absent = service.resolve(_build(vigor_on_back=False), active_bar="front")

    assert SEVENTH_LEGION_BRUTE_POWER_CONDITION in active.condition_context
    assert SEVENTH_LEGION_BRUTE_POWER_CONDITION not in absent.condition_context
    assert any("inactive-bar Vigor" in item for item in active.evidence)


def test_seventh_legion_front_setup_is_verified_when_scored_bar_is_back(tmp_path: Path) -> None:
    build = _build(vigor_on_back=False)
    build.BackBarSkills[0] = "Scored Heal"
    build.FrontBarSkills[0] = "Vigor"
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_ResolveLegality(),
    )

    result = service.resolve(build, active_bar="back")

    assert SEVENTH_LEGION_BRUTE_POWER_CONDITION in result.condition_context
