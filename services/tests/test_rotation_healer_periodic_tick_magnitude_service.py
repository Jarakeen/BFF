from types import SimpleNamespace

from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from models.build_model import PlayerBuild
from services.rotation_healer_action_healing_service import RotationHealerPeriodicHealSeed
from services.rotation_healer_periodic_tick_magnitude_service import (
    RotationHealerPeriodicTickMagnitudeService,
)


class _Coefficients:
    def resolve_name(self, name):
        assert name == "Healing Spring"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=10, entity_id="healing_spring"),
            unresolved=(),
        )


class _Components:
    def __init__(self, classification):
        self.classification = classification

    def get_for_skill_rank(self, skill_rank_id):
        assert skill_rank_id == 10
        return (self.classification,)


class _Tooltip:
    def __init__(self, *, classification, actual=225.0, final=200.0, unresolved=()):
        self.coefficients = _Coefficients()
        self.components = _Components(classification)
        self.actual = actual
        self.final = final
        self.unresolved = tuple(unresolved)
        self.calls = []

    def evaluate_entity_id(self, *, build, context, entity_id):
        self.calls.append((build, context, entity_id))
        actual_trace = () if self.actual is None else (
            SimpleNamespace(coefficient_number=2, output_value=self.actual),
        )
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10),
            components=(SimpleNamespace(coefficient_number=2, final_value=self.final),),
            component_actual_effect_trace=actual_trace,
            unresolved=self.unresolved,
        )


def _classification(*, kind=SkillEffectKind.HEAL, is_dot=True):
    return SkillComponentClassification(
        skill_rank_id=10,
        coefficient_number=2,
        effect_kind=kind,
        is_dot=is_dot,
        source="test",
        confidence=1.0,
    )


def _seed():
    return RotationHealerPeriodicHealSeed(
        time_seconds=1.0,
        sequence=4,
        source_name="Healing Spring",
        coefficient_number=2,
        modeled_heal=100.0,
    )


def test_tick_magnitude_uses_exact_runtime_context_and_actual_effect_value():
    tooltip = _Tooltip(classification=_classification(), actual=225.0)
    service = RotationHealerPeriodicTickMagnitudeService(
        ".",
        tooltip_service=tooltip,
    )
    runtime_context = object()
    calls = []

    def resolver(time_seconds, sequence=None):
        calls.append((time_seconds, sequence))
        return SimpleNamespace(
            resolved=True,
            context=runtime_context,
            active_bar="front",
            unresolved=(),
        )

    build = PlayerBuild()
    result = service.resolve(
        build=build,
        seed=_seed(),
        runtime_build_context_resolver=resolver,
        time_seconds=3.0,
        sequence=4001,
    )

    assert result.resolved
    assert result.modeled_heal == 225.0
    assert calls == [(3.0, 4001)]
    assert tooltip.calls == [(build, runtime_context, "healing_spring")]


def test_tick_magnitude_falls_back_to_component_final_value_when_actual_trace_absent():
    service = RotationHealerPeriodicTickMagnitudeService(
        ".",
        tooltip_service=_Tooltip(
            classification=_classification(),
            actual=None,
            final=190.0,
        ),
    )

    result = service.resolve(
        build=PlayerBuild(),
        seed=_seed(),
        runtime_build_context_resolver=lambda *_: SimpleNamespace(
            resolved=True,
            context=object(),
            active_bar="front",
            unresolved=(),
        ),
        time_seconds=3.0,
        sequence=4001,
    )

    assert result.resolved
    assert result.modeled_heal == 190.0


def test_unresolved_runtime_context_blocks_tick_magnitude_before_tooltip_math():
    tooltip = _Tooltip(classification=_classification())
    service = RotationHealerPeriodicTickMagnitudeService(
        ".",
        tooltip_service=tooltip,
    )

    result = service.resolve(
        build=PlayerBuild(),
        seed=_seed(),
        runtime_build_context_resolver=lambda *_: SimpleNamespace(
            resolved=False,
            context=None,
            active_bar="front",
            unresolved=("runtime buff history incomplete",),
        ),
        time_seconds=3.0,
        sequence=4001,
    )

    assert not result.resolved
    assert result.modeled_heal is None
    assert result.unresolved == ("runtime buff history incomplete",)
    assert tooltip.calls == []


def test_non_periodic_or_non_healing_component_fails_closed():
    service = RotationHealerPeriodicTickMagnitudeService(
        ".",
        tooltip_service=_Tooltip(
            classification=_classification(kind=SkillEffectKind.DAMAGE, is_dot=True),
        ),
    )

    result = service.resolve(
        build=PlayerBuild(),
        seed=_seed(),
        runtime_build_context_resolver=lambda *_: SimpleNamespace(
            resolved=True,
            context=object(),
            active_bar="front",
            unresolved=(),
        ),
        time_seconds=3.0,
        sequence=4001,
    )

    assert not result.resolved
    assert result.unresolved == (
        "component is not canonically classified as healing",
    )
