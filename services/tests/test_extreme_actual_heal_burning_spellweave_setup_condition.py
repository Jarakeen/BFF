from pathlib import Path
import sqlite3

from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    BURNING_SPELLWEAVE_POWER_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitness,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    DEALS_FLAME_DAMAGE,
    ExtremeActualHealSetupActionLegalityService,
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_actual_heal_setup_action_package_adapter import _REVIEWED_SETUP_SETS
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


DESCRIPTION = (
    "(5 items) When you deal damage with a Flame Damage ability, you apply the Burning "
    "status effect to the enemy and increase your Weapon and Spell Damage by 490 for "
    "8 seconds. These effects can occur once every 12 seconds."
)


class _CandidateService:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def candidates(self, context, *, ultimate=None):
        return self.rows


class _NoGearPreconditions:
    @staticmethod
    def resolve(build, *, active_bar="front"):
        return ExtremeActualHealGearPreconditionWitness()


class _FlameLegality:
    @staticmethod
    def witness(capability, context):
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Scalding Rune",
            skill_line="Mages Guild",
            ability_id=12345,
            evidence="route-legal enemy Flame Damage",
        )


def _skill(name: str, description: str) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line="Mages Guild",
        skill_type="Active",
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=12340,
        max_rank=4,
        max_rank_ability_id=12345,
        description=description,
        domain=ExtremeSkillDomain.GUILD,
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
    return path


def _build(*, witness_on_back: bool) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Burning Spellweave"
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = [
        "Scalding Rune" if witness_on_back else "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Back Ultimate",
    ]
    return build


def test_flame_damage_capability_uses_reviewed_enemy_damage_text() -> None:
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_CandidateService(
            (
                _skill("Magic Skill", "Deal 100 Magic Damage to an enemy."),
                _skill(
                    "Scalding Rune",
                    "When triggered, the rune blasts all enemies in the target area for 100 Flame Damage.",
                ),
            )
        )
    )

    witness = service.witness(
        DEALS_FLAME_DAMAGE,
        ExtremePlayerSkillLegalityContext(equipped_class_lines=()),
    )

    assert witness.proven is True
    assert witness.skill_name == "Scalding Rune"
    assert "Flame Damage" in str(witness.evidence)


def test_burning_spellweave_condition_requires_flame_setup_on_inactive_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_FlameLegality(),
    )

    active = service.resolve(_build(witness_on_back=True), active_bar="front")
    absent = service.resolve(_build(witness_on_back=False), active_bar="front")

    assert BURNING_SPELLWEAVE_POWER_CONDITION in active.condition_context
    assert BURNING_SPELLWEAVE_POWER_CONDITION not in absent.condition_context
    assert any("Scalding Rune" in item and "8-second" in item for item in active.evidence)


def test_burning_spellweave_exact_five_piece_maps_to_490_power() -> None:
    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=DESCRIPTION)
    )

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {490.0}
    assert {effect.condition for effect in effects} == {BURNING_SPELLWEAVE_POWER_CONDITION}


def test_burning_spellweave_exact_blocker_is_h1_reviewed() -> None:
    blocker = (
        "Burning Spellweave (5): active set bonus is not yet mechanic-mapped: "
        + DESCRIPTION
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Burning Spellweave",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=129.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)


def test_burning_spellweave_package_generation_owns_flame_setup_slot() -> None:
    assert (
        "Burning Spellweave",
        DEALS_FLAME_DAMAGE,
        "flame-damage",
    ) in _REVIEWED_SETUP_SETS
