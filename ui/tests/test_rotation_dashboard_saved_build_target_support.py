from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_action_target_legality import (
    RotationTargetKind,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
)


class _Generation:
    def __init__(self) -> None:
        self.plan = RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=30.0,
            actions=(),
        )
        self.result = RotationGenerationResult(
            plan=self.plan,
            duration_evidence=SimpleNamespace(summary="seed evidence"),
        )

    def generate_with_evidence(self, **_kwargs):
        return self.result


class _Candidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="ok")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", ""]
    return build


def _request() -> RotationGenerationRequest:
    return RotationGenerationRequest(
        duration_seconds=30.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Combat Prayer",
                priority=10,
            ),
        ),
    )


def _run(support, **kwargs):
    return support.run_effects(
        player_build=_build(),
        generation_request=_request(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        **kwargs,
    )


def test_dashboard_forwards_explicit_target_state_windows() -> None:
    candidates = _Candidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=_Generation(),
        canonical_candidates=candidates,
    )
    window = RotationTargetStateWindow(
        name="Boss target",
        start_seconds=0.0,
        end_seconds=30.0,
        target_kind=RotationTargetKind.ENEMY,
    )

    result = _run(support, target_state_windows=(window,))

    assert result.candidate_result is candidates.result
    assert candidates.calls[0]["target_state_windows"] == (window,)


def test_dashboard_omits_target_keyword_when_no_windows_are_supplied() -> None:
    candidates = _Candidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=_Generation(),
        canonical_candidates=candidates,
    )

    _run(support)

    assert "target_state_windows" not in candidates.calls[0]
