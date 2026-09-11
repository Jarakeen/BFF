from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Parse DD", BuildName="Trial DD", Role="Damage Dealer")
    build.FrontBarSkills = ["Skill A", "", "", "", "", ""]
    return build


def _request() -> RotationGenerationRequest:
    return RotationGenerationRequest(
        duration_seconds=60.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Skill A",
                priority=10,
            ),
        ),
    )


class _Generation:
    def __init__(self) -> None:
        self.result = RotationGenerationResult(
            plan=RotationPlan(
                character_name="Parse DD",
                build_name="Trial DD",
                duration_seconds=60.0,
                actions=(),
            ),
            duration_evidence=SimpleNamespace(summary="seed"),
        )

    def generate_with_evidence(self, **kwargs):
        return self.result


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="canonical")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _support():
    generation = _Generation()
    candidates = _CanonicalCandidates()
    return (
        RotationDashboardCanonicalCandidateSupport(
            generation=generation,
            canonical_candidates=candidates,
        ),
        candidates,
    )


def _base_kwargs() -> dict:
    return dict(
        player_build=_build(),
        generation_request=_request(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
    )


def test_dashboard_forwards_explicit_canonical_role_evidence_unchanged() -> None:
    support, candidates = _support()
    role_evidence = RotationCanonicalRoleEvidence(
        plan_evidence_provider=object(),
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        content_type="trial",
        reliable_group_healing=True,
        exception_contexts=("portal",),
    )

    support.run_effects(
        **_base_kwargs(),
        role_evidence=role_evidence,
    )

    assert len(candidates.calls) == 1
    assert candidates.calls[0]["role_evidence"] is role_evidence


def test_dashboard_legacy_path_omits_role_evidence_when_not_supplied() -> None:
    support, candidates = _support()

    support.run_effects(**_base_kwargs())

    assert len(candidates.calls) == 1
    assert "role_evidence" not in candidates.calls[0]
