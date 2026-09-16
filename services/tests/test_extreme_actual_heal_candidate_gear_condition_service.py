from services.extreme_actual_heal_candidate_gear_condition_service import (
    ExtremeActualHealCandidateGearConditionService,
)
from services.extreme_actual_heal_candidate_scope_service import ExtremeActualHealCandidateScope
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    INNATE_AXIOM_CLASS_SCOPE_CONDITION,
    LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION,
)
from models.build_model import PlayerBuild


class _ScopeService:
    def __init__(self, scope):
        self.scope = scope

    def resolve_entity(self, entity_id):
        return self.scope


def _scope(*, class_ability=False, restoration=False):
    return ExtremeActualHealCandidateScope(
        is_class_ability=class_ability,
        is_weapon_skill_ability=restoration,
        is_restoration_staff_ability=restoration,
        is_area_of_effect=None,
    )


def _build(set_name: str) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = set_name
    return build


def test_light_speaker_activates_only_for_restoration_staff_heal() -> None:
    active = ExtremeActualHealCandidateGearConditionService(
        "unused.db",
        scope_service=_ScopeService(_scope(restoration=True)),
    ).resolve(_build("Light Speaker"), "combat_prayer")
    inactive = ExtremeActualHealCandidateGearConditionService(
        "unused.db",
        scope_service=_ScopeService(_scope(class_ability=True)),
    ).resolve(_build("Light Speaker"), "class_heal")

    assert LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION in active.condition_context
    assert LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION not in inactive.condition_context


def test_innate_axiom_activates_only_for_class_heal() -> None:
    active = ExtremeActualHealCandidateGearConditionService(
        "unused.db",
        scope_service=_ScopeService(_scope(class_ability=True)),
    ).resolve(_build("Innate Axiom"), "class_heal")
    inactive = ExtremeActualHealCandidateGearConditionService(
        "unused.db",
        scope_service=_ScopeService(_scope(restoration=True)),
    ).resolve(_build("Innate Axiom"), "combat_prayer")

    assert INNATE_AXIOM_CLASS_SCOPE_CONDITION in active.condition_context
    assert INNATE_AXIOM_CLASS_SCOPE_CONDITION not in inactive.condition_context


def test_missing_scope_fails_closed_when_scoped_set_is_equipped() -> None:
    result = ExtremeActualHealCandidateGearConditionService(
        "unused.db",
        scope_service=_ScopeService(None),
    ).resolve(_build("Light Speaker"), "unknown_heal")

    assert result.condition_context == frozenset()
    assert result.unresolved
