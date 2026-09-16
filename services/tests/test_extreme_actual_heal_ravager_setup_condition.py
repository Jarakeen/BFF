from pathlib import Path
import sqlite3

from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    RAVAGER_FULL_STACKS_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitness,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


class _NoGearPreconditions:
    @staticmethod
    def resolve(build, *, active_bar="front"):
        return ExtremeActualHealGearPreconditionWitness()


class _ResistanceLegality:
    @staticmethod
    def witness(capability, context):
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Imbue Weapon",
            skill_line="Psijic Order",
            ability_id=12345,
            evidence="route-legal resistance reduction",
        )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
    return path


def _build(*, witness_on_back: bool) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Ravager"
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = [
        "Imbue Weapon" if witness_on_back else "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Back Ultimate",
    ]
    return build


def test_ravager_condition_requires_resistance_witness_on_inactive_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_ResistanceLegality(),
    )

    active = service.resolve(_build(witness_on_back=True), active_bar="front")
    absent = service.resolve(_build(witness_on_back=False), active_bar="front")

    assert RAVAGER_FULL_STACKS_CONDITION in active.condition_context
    assert RAVAGER_FULL_STACKS_CONDITION not in absent.condition_context
    assert any("four qualifying attempts" in item for item in active.evidence)
    assert any("10-second" in item for item in active.evidence)


def test_ravager_exact_five_piece_maps_to_584_power() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Each time you attempt to reduce the target's Physical or Spell Resistance, "
            "you gain a stack of Ravager for 5 seconds, increasing your Weapon and Spell Damage "
            "by 146. You can gain a stack every 1 second. At 4 stacks, the duration doubles but "
            "cannot be refreshed."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {584.0}
    assert {effect.condition for effect in effects} == {RAVAGER_FULL_STACKS_CONDITION}


def test_ravager_exact_blocker_is_h1_reviewed() -> None:
    blocker = (
        "Ravager (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Each time you attempt to reduce the target's Physical or Spell Resistance, "
        "you gain a stack of Ravager for 5 seconds, increasing your Weapon and Spell Damage by "
        "146. You can gain a stack every 1 second. At 4 stacks, the duration doubles but cannot "
        "be refreshed."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Ravager",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
