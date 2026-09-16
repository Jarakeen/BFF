from pathlib import Path
import sqlite3

from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    CRUSADER_MINOR_COURAGE_CONDITION,
    ExtremeActualHealGearPreconditionWitness,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    DEALS_DIRECT_MOBILITY_DAMAGE,
    ExtremeActualHealSetupActionLegalityService,
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_actual_heal_setup_action_package_adapter import _REVIEWED_SETUP_SETS
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


DESCRIPTION = (
    "(5 items) When you deal direct damage with a Blink, Charge, Leap, Teleport, or Pull "
    "ability, you consecrate the ground beneath you for 10 seconds and gain a damage shield "
    "that absorbs 1596 damage for 6 seconds. Every 2 seconds you and nearby group members in "
    "the area gain Minor Courage for 12 seconds. These effects can occur once every 20 seconds "
    "and the damage shield scales off the higher of your Weapon or Spell Damage."
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


class _MobilityLegality:
    @staticmethod
    def witness(capability, context):
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Silver Leash",
            skill_line="Fighters Guild",
            ability_id=12345,
            evidence="route-legal direct-damage Pull ability",
        )


def _skill(name: str, description: str) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line="Fighters Guild",
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
        build.Armor[slot]["Set"] = "Crusader"
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = [
        "Silver Leash" if witness_on_back else "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Back Ultimate",
    ]
    return build


def test_direct_mobility_capability_requires_direct_damage_and_trigger_movement() -> None:
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_CandidateService(
            (
                _skill("Pull Only", "Pull the enemy to you."),
                _skill("Damage Only", "Deal 100 Physical Damage to an enemy."),
                _skill(
                    "Silver Leash",
                    "Fire a crossbow bolt to pull an enemy to you, dealing 100 Physical Damage.",
                ),
            )
        )
    )

    witness = service.witness(
        DEALS_DIRECT_MOBILITY_DAMAGE,
        ExtremePlayerSkillLegalityContext(equipped_class_lines=()),
    )

    assert witness.proven is True
    assert witness.skill_name == "Silver Leash"
    assert "direct damage" in str(witness.evidence)


def test_periodic_only_mobility_damage_fails_closed() -> None:
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_CandidateService(
            (
                _skill(
                    "Slow Pull",
                    "Pull the enemy to you, dealing 100 Physical Damage over 10 seconds.",
                ),
            )
        )
    )
    witness = service.witness(
        DEALS_DIRECT_MOBILITY_DAMAGE,
        ExtremePlayerSkillLegalityContext(equipped_class_lines=()),
    )
    assert witness.proven is False


def test_crusader_condition_requires_mobility_setup_on_inactive_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_MobilityLegality(),
    )

    active = service.resolve(_build(witness_on_back=True), active_bar="front")
    absent = service.resolve(_build(witness_on_back=False), active_bar="front")

    assert CRUSADER_MINOR_COURAGE_CONDITION in active.condition_context
    assert CRUSADER_MINOR_COURAGE_CONDITION not in absent.condition_context
    assert any("Silver Leash" in item and "12-second Minor Courage" in item for item in active.evidence)


def test_crusader_condition_enters_canonical_minor_courage_state() -> None:
    state = ExtremeResourceConditionedPhase5ContextFactory._combat_state_with_reviewed_gear_witnesses(
        CombatState(),
        frozenset({CRUSADER_MINOR_COURAGE_CONDITION}),
    )

    assert "Minor Courage" in state.active_buffs
    assert state.in_combat is True


def test_crusader_exact_blocker_is_h1_reviewed() -> None:
    blocker = "Crusader (5): active set bonus is not yet mechanic-mapped: " + DESCRIPTION
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Crusader",
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


def test_crusader_package_generation_owns_real_setup_slot() -> None:
    assert (
        "Crusader",
        DEALS_DIRECT_MOBILITY_DAMAGE,
        "direct-mobility-damage",
    ) in _REVIEWED_SETUP_SETS
