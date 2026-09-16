from pathlib import Path
import sqlite3

from minmax.effect_kinds import EffectKind
from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_set_resource_condition_resolver import GearSetResourceConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import ExtremeActualHealBuildConditionContextService
from services.extreme_actual_heal_gear_precondition_witness_service import ExtremeActualHealGearPreconditionWitness
from services.extreme_actual_heal_gear_set_candidate_service import ExtremeActualHealGearSetCandidateService
from services.extreme_actual_heal_setup_action_legality_service import (
    IS_ARMOR_ABILITY,
    ExtremeActualHealSetupActionLegalityService,
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_actual_heal_setup_action_package_adapter import _REVIEWED_ACTIVE_BAR_SLOTTED_SETS
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


DESCRIPTION = (
    "(5 items) While you have an Armor ability slotted, your Max Health is increased by 5%. "
    "When you use an Armor ability while in combat, your Physical and Spell Resistance is "
    "increased by 138-5940 for 10 seconds."
)


class _CandidateService:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def candidates(self, context, *, ultimate=None):
        return tuple(
            row for row in self.rows
            if not context.equipped_armor_lines or row.skill_line in context.equipped_armor_lines
        )


class _NoGearPreconditions:
    @staticmethod
    def resolve(build, *, active_bar="front"):
        return ExtremeActualHealGearPreconditionWitness()


class _ArmorLegality:
    @staticmethod
    def witness(capability, context):
        if "Light Armor" not in context.equipped_armor_lines:
            return ExtremeActualHealSetupActionWitness(capability=capability, unresolved=("Light Armor is not worn",))
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name="Annulment",
            skill_line="Light Armor",
            ability_id=12345,
            evidence="equipped Light Armor active",
        )


def _skill(line: str, domain: ExtremeSkillDomain) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name="Annulment",
        class_type="",
        skill_line=line,
        skill_type="Active",
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=12340,
        max_rank=4,
        max_rank_ability_id=12345,
        description="Convert a portion of your Magicka into a protective ward.",
        domain=domain,
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
    return path


def _build(*, active_bar_has_witness: bool) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = "Armor Master"
        build.Armor[slot]["Weight"] = "Light"
    build.FrontBarSkills = ["Scored Heal", "Annulment" if active_bar_has_witness else "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["One", "Two", "Three", "Four", "Five", "Back Ultimate"]
    return build


def test_armor_capability_requires_equipped_armor_domain_active() -> None:
    service = ExtremeActualHealSetupActionLegalityService(
        candidate_service=_CandidateService((
            _skill("Light Armor", ExtremeSkillDomain.ARMOR),
            _skill("Mages Guild", ExtremeSkillDomain.GUILD),
        ))
    )
    witness = service.witness(
        IS_ARMOR_ABILITY,
        ExtremePlayerSkillLegalityContext(equipped_class_lines=(), equipped_armor_lines=("Light Armor",)),
    )
    assert witness.proven is True
    assert witness.skill_line == "Light Armor"


def test_armor_master_condition_requires_witness_on_scored_active_bar(tmp_path: Path) -> None:
    service = ExtremeActualHealBuildConditionContextService(
        _database(tmp_path),
        gear_preconditions=_NoGearPreconditions(),
        setup_action_legality=_ArmorLegality(),
    )
    active = service.resolve(_build(active_bar_has_witness=True), active_bar="front")
    absent = service.resolve(_build(active_bar_has_witness=False), active_bar="front")
    assert "armor_ability_slotted" in active.condition_context
    assert "armor_ability_slotted" not in absent.condition_context
    assert any("scored active-bar Annulment" in item for item in active.evidence)


def test_armor_master_maps_five_percent_max_health_condition() -> None:
    effects = GearSetResourceConditionResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=DESCRIPTION)
    )
    assert len(effects) == 1
    effect = effects[0]
    assert effect.stat == StatId.MAX_HEALTH
    assert effect.value == 5.0
    assert effect.condition == "armor_ability_slotted"
    assert effect.operation is EffectOperation.ADD_PERCENT
    assert effect.unit is EffectUnit.PERCENT
    assert effect.kind is EffectKind.STAT


def test_armor_master_package_owns_active_bar_slotted_slot() -> None:
    assert ("Armor Master", IS_ARMOR_ABILITY, "armor-ability-slotted") in _REVIEWED_ACTIVE_BAR_SLOTTED_SETS

def test_armor_master_exact_percentage_reference_blocker_is_h1_reviewed() -> None:
    blocker = (
        "Armor Master (5): relevant percentage set effect requires "
        "objective-specific stacking/reference review"
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Armor Master",
        category="Test",
        equipped_piece_count=5,
        objective_key="max_health",
        reviewed_delta=1206.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.ignored_blockers == (blocker,)
    assert result.remaining_blockers == ()

