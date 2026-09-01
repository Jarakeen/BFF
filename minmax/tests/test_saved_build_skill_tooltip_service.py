from types import SimpleNamespace

from models.build_model import ChampionPointEntry, PlayerBuild

from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_actual_effect_modifiers import SkillComponentActualEffectModifier
from minmax.skill_component_classification import SkillEffectKind


class _CoefficientRepository:
    def resolve_entity_id(self, entity_id):
        return SimpleNamespace(rank=SimpleNamespace(skill_rank_id=1234))


class _ComponentRepository:
    def get_for_skill_rank(self, skill_rank_id):
        assert skill_rank_id == 1234
        return (
            SimpleNamespace(coefficient_number=1, effect_kind=SkillEffectKind.HEAL),
            SimpleNamespace(coefficient_number=2, effect_kind=SkillEffectKind.DAMAGE),
            SimpleNamespace(coefficient_number=3, effect_kind=SkillEffectKind.HEAL),
        )


class _HealingResolver:
    def __init__(self):
        self.calls = []

    def resolve_for_skill(self, **kwargs):
        self.calls.append(kwargs)
        return (
            (
                SkillComponentActualEffectModifier(
                    coefficient_number=1,
                    power_bonus=205.0,
                    additive_percent=10.0,
                    sources=("Rejuvenator", "Soothing Tide"),
                ),
            ),
            (),
        )


class _Calculator:
    def __init__(self):
        self.calls = []
        self.result = SimpleNamespace(unresolved=())

    def evaluate_entity_id(self, entity_id, context, **kwargs):
        self.calls.append((entity_id, context, kwargs))
        return self.result


def test_saved_build_service_routes_only_heal_components_and_marks_saved_cp_as_slotted():
    cp_resolver = _HealingResolver()
    calculator = _Calculator()
    service = SavedBuildSkillTooltipService(
        "unused.db",
        coefficient_repository=_CoefficientRepository(),
        component_repository=_ComponentRepository(),
        healing_cp_resolver=cp_resolver,
        calculator=calculator,
    )
    build = PlayerBuild(
        ChampionPoints=[
            ChampionPointEntry(Name="Rejuvenator", Points="50"),
            ChampionPointEntry(Name="Soothing Tide", Points="50"),
        ]
    )
    context = object()

    result = service.evaluate_entity_id(
        build=build,
        context=context,
        entity_id="energy_orb",
    )

    assert result is calculator.result
    assert len(cp_resolver.calls) == 1
    call = cp_resolver.calls[0]
    assert call["skill_rank_id"] == 1234
    assert call["coefficient_numbers"] == (1, 3)
    assert call["is_slotted"] is True
    assert [(row.node_id, row.points) for row in call["allocations"]] == [
        ("rejuvenator", 50),
        ("soothing_tide", 50),
    ]

    assert len(calculator.calls) == 1
    entity_id, passed_context, kwargs = calculator.calls[0]
    assert entity_id == "energy_orb"
    assert passed_context is context
    modifiers = kwargs["component_actual_effect_modifiers"]
    assert len(modifiers) == 1
    assert modifiers[0].coefficient_number == 1
    assert modifiers[0].power_bonus == 205.0
    assert modifiers[0].additive_percent == 10.0
