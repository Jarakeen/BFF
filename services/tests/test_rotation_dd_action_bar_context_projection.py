from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from services.rotation_dd_action_damage_event_service import RotationDDActionDamageEventService


class _Coefficients:
    def resolve_name(self, name):
        return SimpleNamespace(rank=SimpleNamespace(skill_rank_id=10), unresolved=())


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        return (
            SkillComponentClassification(
                skill_rank_id=skill_rank_id,
                coefficient_number=1,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=False,
                is_aoe=False,
                can_crit=True,
                source="test",
                confidence=1.0,
            ),
        )


class _Calculator:
    def __init__(self):
        self.seen = []

    def evaluate_name(self, name, context):
        self.seen.append((name, context.marker))
        value = 100.0 if context.marker == "front" else 200.0
        return SimpleNamespace(
            components=(SimpleNamespace(coefficient_number=1, final_value=value),),
            unresolved=(),
        )


def _service(calculator):
    return RotationDDActionDamageEventService(
        ".",
        coefficient_repository=_Coefficients(),
        component_repository=_Components(),
        calculator=calculator,
    )


def test_skill_tooltip_projection_uses_context_for_exact_action_order():
    calculator = _Calculator()
    service = _service(calculator)
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=8.0,
        actions=(
            RotationAction(1.0, 10, RotationActionKind.SKILL, name="Front Hit", bar="front"),
            RotationAction(4.0, 20, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(4.0, 21, RotationActionKind.SKILL, name="Back Hit", bar="back"),
        ),
    )
    front = SimpleNamespace(marker="front")
    back = SimpleNamespace(marker="back")
    calls = []

    def context_at(time_seconds, sequence):
        calls.append((time_seconds, sequence))
        return front if (time_seconds, sequence) < (4.0, 20) else back

    projection = service.project(
        plan=plan,
        context=front,
        context_resolver=context_at,
    )

    assert calls == [(1.0, 10), (4.0, 21)]
    assert calculator.seen == [("Front Hit", "front"), ("Back Hit", "back")]
    assert [event.event.base_value for event in projection.events] == [100.0, 200.0]
    assert projection.unresolved == ()


def test_context_resolution_failure_is_explicit_unresolved_damage_evidence():
    calculator = _Calculator()
    service = _service(calculator)
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=5.0,
        actions=(
            RotationAction(2.0, 7, RotationActionKind.SKILL, name="Hit", bar="front"),
        ),
    )

    def missing_context(time_seconds, sequence):
        raise ValueError("back-bar static context missing")

    projection = service.project(
        plan=plan,
        context=SimpleNamespace(marker="front"),
        context_resolver=missing_context,
    )

    assert projection.events == ()
    assert projection.unresolved == (
        "Hit at 2s: active-bar damage context unavailable: back-bar static context missing",
    )
    assert calculator.seen == []
