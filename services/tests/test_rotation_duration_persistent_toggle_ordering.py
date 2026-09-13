from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastAnalysis
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_duration_refinement_service import RotationDurationRefinementService


class _DurationAnalysis:
    def __init__(self):
        self.calls = []

    def analyze(self, plan, **kwargs):
        self.calls.append(plan)
        return RotationDurationProjection(
            analysis=RotationRecastAnalysis(windows=(), summaries=()),
            rules=(),
            unresolved=(),
        )


class _Scheduler:
    def __init__(self):
        self.received = None

    def refine(self, plan, rules, **kwargs):
        self.received = plan
        return plan


def _action(time_seconds, sequence, kind, name=None, bar=None):
    return RotationAction(
        time_seconds=float(time_seconds),
        sequence=int(sequence),
        kind=kind,
        name=name,
        bar=bar,
    )


def test_persistent_toggle_is_normalized_before_duration_scheduler_receives_seed() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=6.0,
        actions=(
            _action(0, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
            _action(1, 1, RotationActionKind.SKILL, "Venom Skull", "front"),
            _action(2, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _action(3, 1, RotationActionKind.SKILL, "Magical Banner", "back"),
            _action(4, 1, RotationActionKind.SKILL, "Resolving Vigor", "back"),
            _action(5, 0, RotationActionKind.BAR_SWAP, bar="front"),
            _action(6, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
        ),
    )
    analysis = _DurationAnalysis()
    scheduler = _Scheduler()

    result = RotationDurationRefinementService(
        duration_analysis=analysis,
        scheduler=scheduler,
    ).refine(plan)

    assert scheduler.received is not None
    banner_actions = [
        action
        for action in scheduler.received.actions
        if action.kind is RotationActionKind.SKILL and action.name == "Magical Banner"
    ]
    assert [(action.time_seconds, action.bar) for action in banner_actions] == [(0.0, "front")]
    assert next(
        action
        for action in scheduler.received.actions
        if action.time_seconds == 3.0 and action.sequence == 1
    ).name == "Resolving Vigor"
    assert next(
        action
        for action in scheduler.received.actions
        if action.time_seconds == 6.0 and action.sequence == 1
    ).name == "Venom Skull"
    assert result.plan.actions == scheduler.received.actions
