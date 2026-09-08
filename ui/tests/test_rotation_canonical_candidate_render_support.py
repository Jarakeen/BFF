from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from ui.rotation_canonical_candidate_render_support import (
    RotationCanonicalCandidateRenderSupport,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name=name,
                bar="front",
            ),
        ),
    )


class _DurationEvidence:
    def __init__(self) -> None:
        self.calls = []

    def build(self, plan):
        self.calls.append(plan)
        return SimpleNamespace(source_plan=plan)


def _application_result(*, selected=True, selectable=True):
    seed_plan = _plan("Seed Skill")
    final_plan = _plan("Final Skill")
    other_plan = _plan("Other Skill")
    final_projection = SimpleNamespace(source="final recovery replay")
    other_projection = SimpleNamespace(source="other recovery replay")
    effect_assessment = SimpleNamespace(effect="Major Brittle")

    selected_candidate = None
    if selected:
        selected_candidate = SimpleNamespace(
            candidate_id="winner",
            selectable=selectable,
            evaluation=SimpleNamespace(
                candidate_id="winner",
                effect_uptime_assessments=(effect_assessment,),
            ),
        )

    pipeline = SimpleNamespace(
        selected_candidate=selected_candidate,
        stabilized_candidates=(
            SimpleNamespace(
                candidate_id="other",
                plan=other_plan,
                replay=SimpleNamespace(final_projection=other_projection),
            ),
            SimpleNamespace(
                candidate_id="winner",
                plan=final_plan,
                replay=SimpleNamespace(final_projection=final_projection),
            ),
        ),
    )
    result = SimpleNamespace(
        build_adaptation=SimpleNamespace(),
        pipeline_result=pipeline,
        validation=SimpleNamespace(selectable=True),
    )
    return result, seed_plan, final_plan, final_projection, effect_assessment


def test_render_evidence_uses_selected_final_stabilized_plan_only() -> None:
    duration = _DurationEvidence()
    support = RotationCanonicalCandidateRenderSupport(duration_evidence=duration)
    result, seed_plan, final_plan, final_projection, effect_assessment = _application_result()

    evidence = support.build(result)

    assert evidence is not None
    assert evidence.candidate_id == "winner"
    assert evidence.plan is final_plan
    assert evidence.plan is not seed_plan
    assert evidence.sustain_projection is final_projection
    assert evidence.duration_evidence.source_plan is final_plan
    assert duration.calls == [final_plan]
    assert evidence.effect_uptime_assessments == (effect_assessment,)


def test_render_evidence_returns_none_without_canonical_selection() -> None:
    duration = _DurationEvidence()
    support = RotationCanonicalCandidateRenderSupport(duration_evidence=duration)
    result, *_ = _application_result(selected=False)

    assert support.build(result) is None
    assert duration.calls == []

    result.pipeline_result = None
    assert support.build(result) is None
    assert duration.calls == []


def test_render_evidence_rejects_nonselectable_or_ambiguous_selection() -> None:
    support = RotationCanonicalCandidateRenderSupport(duration_evidence=_DurationEvidence())
    result, *_ = _application_result(selectable=False)

    with pytest.raises(ValueError, match="nonselectable"):
        support.build(result)

    result, *_ = _application_result()
    duplicate = result.pipeline_result.stabilized_candidates[1]
    result.pipeline_result.stabilized_candidates += (duplicate,)

    with pytest.raises(ValueError, match="exactly one"):
        support.build(result)
