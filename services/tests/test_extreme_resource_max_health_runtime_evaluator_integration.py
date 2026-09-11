from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphPieceChoice,
    ExtremeArmorResourceTraitGlyphState,
)
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightState,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
)
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)
from services.extreme_resource_max_health_runtime_state_service import (
    ExtremeResourceMaxHealthRuntimeState,
)


class _ProgressionService:
    def normalize(self, progression, route):
        return progression


class _Optimizer:
    def objective(self, key):
        return SimpleNamespace(key=key)

    @staticmethod
    def _objective_value(context, objective):
        return context.value


class _NamedGearEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        build = PlayerBuild(EsoClass="Necromancer")
        build.Race = candidate.race
        return 100.0, {"build": build.to_dict()}, ()


_RUNTIME_STATE = ExtremeResourceMaxHealthRuntimeState(
    label="Nothing Wasted 10 stacks",
    nothing_wasted_stacks=10,
    class_mastery_ability_ids=(987654,),
    reviewed_percent_bonus=0.20,
    conditions=("Maximum 10-stack Nothing Wasted state; stacks require Corpse Consumption activity.",),
)


class _RuntimeStateService:
    def build(self, route):
        return SimpleNamespace(
            states=(_RUNTIME_STATE,),
            denominator_proven=True,
            unresolved=(),
        )

    @staticmethod
    def materialize(build, state):
        result = PlayerBuild.from_dict(build.to_dict())
        result.ClassMasteryAbilityIds = list(state.class_mastery_ability_ids)
        return result


class _RuntimeContextService:
    def __init__(self):
        self.last_build = None
        self.last_progression = None
        self.last_state = None

    def resolve(self, *, build, progression, state, **kwargs):
        self.last_build = build
        self.last_progression = progression
        self.last_state = state
        return SimpleNamespace(value=5555.0, unresolved_gear_effects=())


class _ContextFactory:
    pass


def _armor_state():
    slots = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    pieces = tuple(
        ExtremeArmorResourceTraitGlyphPieceChoice(
            slot=slot,
            trait="Divines",
            enchant="Max Health",
            direct_delta=100.0,
        )
        for slot in slots
    )
    trait_glyph = ExtremeArmorResourceTraitGlyphState(
        objective_key="max_health",
        pieces=pieces,
        direct_glyph_delta=700.0,
    )
    weights = tuple((slot, "Heavy") for slot in slots)
    weight = ExtremeArmorResourceWeightState(
        objective_key="max_health",
        weights=weights,
    )
    return ExtremeArmorResourceWeightTraitGlyphState(
        objective_key="max_health",
        weight_state=weight,
        trait_glyph_state=trait_glyph,
    )


def _candidate():
    return SimpleNamespace(
        race="Nord",
        attributes=SimpleNamespace(health=64, magicka=0, stamina=0),
        class_route=SimpleNamespace(),
        active_bar="front",
        identity=("Nord", "Necromancer", (), 64, 0, 0, "front"),
    )


def test_max_health_evaluator_materializes_runtime_witness_into_canonical_context():
    runtime_context = _RuntimeContextService()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=_NamedGearEvaluator(),
        armor_state=_armor_state(),
        max_health_runtime_state_service=_RuntimeStateService(),
        max_health_runtime_context_service=runtime_context,
        context_factory=_ContextFactory(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate("max_health", _candidate())

    assert value == 5555.0
    assert unresolved == ()
    assert runtime_context.last_state is _RUNTIME_STATE
    assert runtime_context.last_build.ClassMasteryAbilityIds == [987654]
    assert payload["resource_max_health_runtime_label"] == "Nothing Wasted 10 stacks"
    assert payload["resource_max_health_runtime_nothing_wasted_stacks"] == 10
    assert payload["resource_max_health_runtime_class_mastery_ability_ids"] == (987654,)
    assert payload["resource_max_health_runtime_reviewed_percent_bonus"] == 0.20
    assert payload["resource_max_health_runtime_denominator_proven"] is True
