from pathlib import Path
import sqlite3

from minmax.gear_sets import GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    POWERFUL_ASSAULT_POWER_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
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


class _AssaultLegality:
    @staticmethod
    def witness(capability, context):
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Vigor",
            skill_line="Assault",
            ability_id=12345,
            evidence="route-legal Assault active",
        )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
    return path


def _build(*, witness_on_back: bool) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Powerful Assault"
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = [
        "Vigor" if witness_on_back else "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Back Ultimate",
    ]
    return build


def test_powerful_assault_condition_requires_assault_witness_on_inactive_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_AssaultLegality(),
    )

    active = service.resolve(_build(witness_on_back=True), active_bar="front")
    absent = service.resolve(_build(witness_on_back=False), active_bar="front")

    assert POWERFUL_ASSAULT_POWER_CONDITION in active.condition_context
    assert POWERFUL_ASSAULT_POWER_CONDITION not in absent.condition_context
    assert any("inactive-bar Vigor" in item for item in active.evidence)


def test_powerful_assault_exact_five_piece_maps_to_307_power() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When you cast an Assault ability while in combat, you and up to 5 group "
            "members within 12 meters gain 307 Weapon and Spell Damage for 15 seconds."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert len(effects) == 2
    assert {effect.value for effect in effects} == {307.0}
    assert {effect.condition for effect in effects} == {POWERFUL_ASSAULT_POWER_CONDITION}
