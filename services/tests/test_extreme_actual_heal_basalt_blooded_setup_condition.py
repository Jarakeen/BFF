from pathlib import Path
import sqlite3

from minmax.gear_set_healing_condition_resolver import GearSetHealingConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION,
    ExtremeActualHealGearPreconditionWitness,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_setup_action_legality_service import (
    IS_EARTHEN_HEART_ABILITY,
    ExtremeActualHealSetupActionLegalityService,
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_actual_heal_setup_action_package_adapter import _REVIEWED_SETUP_SETS
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


DESCRIPTION = (
    "(5 items) Casting an Earthen Heart ability grants you a Rock Stance for 10 seconds. "
    "While on your Primary Weapon you gain Molten Stance, granting you Major Heroism, "
    "generating 3 Ultimate every 1.5 seconds. While you are on your Secondary Weapon you "
    "gain Obsidian Stance, increasing your Healing Done and damage shields by 14%. "
    "Bar Swapping will swap your Stance automatically."
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


class _EarthenHeartLegality:
    @staticmethod
    def witness(capability, context):
        explicit = {
            str(value).strip().casefold().replace(" ", "_")
            for value in context.equipped_class_lines
        }
        if "earthen_heart" not in explicit:
            return ExtremeActualHealSetupActionWitness(
                capability=capability,
                unresolved=("Earthen Heart is not route-legal",),
            )
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Igneous Shield",
            skill_line="Earthen Heart",
            ability_id=12345,
            evidence="route-legal Earthen Heart ability",
        )


def _skill(line: str) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name="Igneous Shield",
        class_type="Dragonknight",
        skill_line=line,
        skill_type="Active",
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=12340,
        max_rank=4,
        max_rank_ability_id=12345,
        description="Call the earth to your defense.",
        domain=ExtremeSkillDomain.CLASS,
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
    return path


def _build() -> PlayerBuild:
    build = PlayerBuild(ClassSkillLines=["earthen_heart", "green_balance", "siphoning"])
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Basalt-Blooded Warrior"
    build.FrontBarSkills = ["Igneous Shield", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["Scored Heal", "One", "Two", "Three", "Four", "Back Ultimate"]
    return build


def test_earthen_heart_capability_uses_canonical_skill_line_identity() -> None:
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_CandidateService((_skill("Draconic Power"), _skill("Earthen Heart")))
    )
    witness = service.witness(
        IS_EARTHEN_HEART_ABILITY,
        ExtremePlayerSkillLegalityContext(equipped_class_lines=("earthen_heart",)),
    )
    assert witness.proven is True
    assert witness.skill_line == "Earthen Heart"


def test_basalt_condition_requires_front_setup_and_back_scored_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_EarthenHeartLegality(),
    )
    back = service.resolve(_build(), active_bar="back")
    front = service.resolve(_build(), active_bar="front")
    assert BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION in back.condition_context
    assert BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION not in front.condition_context
    assert any("primary/front-bar Igneous Shield" in item for item in back.evidence)


def test_basalt_exact_five_piece_maps_to_fourteen_percent_healing_done() -> None:
    effects = GearSetHealingConditionResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=DESCRIPTION)
    )
    assert len(effects) == 1
    assert effects[0].stat == StatId.HEALING_DONE
    assert effects[0].value == 14.0
    assert effects[0].condition == BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION


def test_basalt_canonical_markup_and_fused_spacing_maps_to_healing_done() -> None:
    canonical = (
        "(5 items) Casting an Earthen Heart ability grants you a Rock Stance for "
        "|cffffff10|r seconds. While on your Primary Weapon you gain Molten Stance, "
        "granting you Major Heroism, generating |cffffff3|r Ultimate every "
        "|cffffff1.5|r seconds. While youare on your Secondary Weapon you gain "
        "Obsidian Stance, increasing your Healing Done and damage shields by "
        "|cffffff14|r%. \n\nBar Swapping will swap your Stance automatically."
    )
    effects = GearSetHealingConditionResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=canonical)
    )
    assert len(effects) == 1
    assert effects[0].stat == StatId.HEALING_DONE
    assert effects[0].value == 14.0
    assert effects[0].condition == BASALT_BLOODED_OBSIDIAN_STANCE_CONDITION


def test_basalt_exact_blocker_is_h1_reviewed_only_for_healing_done() -> None:
    blocker = "Basalt-Blooded Warrior (5): active set bonus is not yet mechanic-mapped: " + DESCRIPTION
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Basalt-Blooded Warrior",
        category="Test",
        equipped_piece_count=5,
        objective_key="healing_done",
        reviewed_delta=14.0,
        unresolved=(blocker,),
    )
    result = ExtremeActualHealGearSetCandidateService._h1_review(row)
    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)


def test_basalt_package_generation_owns_earthen_heart_setup_slot() -> None:
    assert (
        "Basalt-Blooded Warrior",
        IS_EARTHEN_HEART_ABILITY,
        "earthen-heart",
    ) in _REVIEWED_SETUP_SETS
