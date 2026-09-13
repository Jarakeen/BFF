import math
from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_duration_analysis_service import RotationDurationAnalysisService


class _DurationRepository:
    def __init__(self):
        self.calls = []

    def resolve_name(self, name):
        self.calls.append(name)
        return SimpleNamespace(
            duration_seconds=None,
            unresolved=(f"unexpected duration lookup: {name}",),
            skill_name=name,
        )


def test_reviewed_persistent_toggle_emits_scheduler_rules_without_duration_lookup() -> None:
    repository = _DurationRepository()
    service = RotationDurationAnalysisService(
        duration_repository=repository,  # type: ignore[arg-type]
    )
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Magical Banner",
                bar="front",
            ),
            RotationAction(
                time_seconds=5.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Magical Banner",
                bar="back",
            ),
        ),
    )

    projection = service.analyze(plan)

    assert repository.calls == []
    assert [(rule.skill_name, rule.bar, rule.persistent) for rule in projection.rules] == [
        ("Magical Banner", "front", True),
        ("Magical Banner", "back", True),
    ]
    assert all(math.isinf(float(rule.duration_seconds)) for rule in projection.rules)
    assert projection.unresolved == ()
    assert projection.analysis.windows == ()
    assert projection.analysis.summaries == ()
    assert projection.analysis.unresolved == ()
