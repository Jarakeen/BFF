from dataclasses import dataclass

from minmax.gear_sets import GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_candidate_gear_condition_service import (
    ExtremeActualHealCandidateGearConditionService,
)
from services.extreme_actual_heal_candidate_scope_service import ExtremeActualHealCandidateScope
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    INNATE_AXIOM_CLASS_SCOPE_CONDITION,
    LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


@dataclass
class _ScopeStub:
    rows: dict[str, ExtremeActualHealCandidateScope]

    def resolve_entity(self, entity_id: str):
        return self.rows.get(entity_id)


def _scope(*, class_ability: bool, restoration: bool) -> ExtremeActualHealCandidateScope:
    return ExtremeActualHealCandidateScope(
        is_class_ability=class_ability,
        is_weapon_skill_ability=restoration,
        is_restoration_staff_ability=restoration,
        is_area_of_effect=None,
        evidence=(),
        unresolved=(),
    )


def _build(set_name: str) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = set_name
    return build


def test_candidate_scoped_conditions_follow_selected_heal_identity(tmp_path) -> None:
    scopes = _ScopeStub(
        {
            "combat_prayer": _scope(class_ability=False, restoration=True),
            "budding_seeds": _scope(class_ability=True, restoration=False),
        }
    )

    light = ExtremeActualHealCandidateGearConditionService(
        tmp_path / "eso.db",
        scope_service=scopes,
    )
    light_for_restoration = light.resolve(_build("Light Speaker"), "combat_prayer")
    light_for_class = light.resolve(_build("Light Speaker"), "budding_seeds")
    innate_for_restoration = light.resolve(_build("Innate Axiom"), "combat_prayer")
    innate_for_class = light.resolve(_build("Innate Axiom"), "budding_seeds")

    assert LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION in light_for_restoration.condition_context
    assert LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION not in light_for_class.condition_context
    assert INNATE_AXIOM_CLASS_SCOPE_CONDITION not in innate_for_restoration.condition_context
    assert INNATE_AXIOM_CLASS_SCOPE_CONDITION in innate_for_class.condition_context


def test_scoped_effects_map_exact_reviewed_values() -> None:
    resolver = ExtremeActualHealGearPreconditionEffectResolver()
    light = resolver.resolve(
        GearSetBonus(
            id=1,
            set_id=1,
            piece_count=5,
            description="(5 items) Adds 600 Weapon and Spell Damage to your Restoration Staff abilities.",
        )
    )
    innate = resolver.resolve(
        GearSetBonus(
            id=2,
            set_id=2,
            piece_count=5,
            description="(5 items) Adds 400 Weapon and Spell Damage to your Class abilities.",
        )
    )

    assert {effect.value for effect in light} == {600.0}
    assert {effect.condition for effect in light} == {LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION}
    assert {effect.value for effect in innate} == {400.0}
    assert {effect.condition for effect in innate} == {INNATE_AXIOM_CLASS_SCOPE_CONDITION}


def test_exact_candidate_scoped_blockers_are_h1_mechanic_complete() -> None:
    cases = (
        (
            "Light Speaker",
            "Light Speaker (5): active set bonus is not yet mechanic-mapped: "
            "(5 items) Adds 600 Weapon and Spell Damage to your Restoration Staff abilities.",
        ),
        (
            "Innate Axiom",
            "Innate Axiom (5): active set bonus is not yet mechanic-mapped: "
            "(5 items) Adds 400 Weapon and Spell Damage to your Class abilities.",
        ),
    )
    for index, (set_name, blocker) in enumerate(cases, start=1):
        row = ExtremeGearSetObjectiveCandidate(
            set_id=index,
            set_name=set_name,
            category="Test",
            equipped_piece_count=5,
            objective_key="spell_damage",
            reviewed_delta=0.0,
            unresolved=(blocker,),
        )
        review = ExtremeActualHealGearSetCandidateService._h1_review(row)
        assert review.h1_mechanic_complete is True
        assert review.h1_positive_modifier_proven is True
        assert review.remaining_blockers == ()
        assert review.ignored_blockers == (blocker,)


def test_unreviewed_scoped_lookalike_stays_unresolved() -> None:
    blocker = (
        "Mystery Scoped Set (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Adds 600 Weapon and Spell Damage to your Restoration Staff abilities."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=9,
        set_name="Mystery Scoped Set",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    review = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert review.h1_mechanic_complete is False
    assert review.remaining_blockers == (blocker,)
