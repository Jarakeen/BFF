from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from services.extreme_sustained_dps_execute_policy_frontier_service import (
    ExtremeSustainedDPSExecutePolicyFrontierService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _candidate(candidate_id="seed"):
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
    )


class _Policy:
    def __init__(self, *, mutations=(), unresolved=()):
        self.mutations = tuple(mutations)
        self.unresolved = tuple(unresolved)

    def apply(self, **kwargs):
        candidate = _candidate("execute") if self.mutations else kwargs["candidate"]
        return SimpleNamespace(
            candidate=candidate,
            mutations=self.mutations,
            unresolved=self.unresolved,
        )


def test_execute_policy_keeps_baseline_and_canonical_mutation_separate() -> None:
    service = ExtremeSustainedDPSExecutePolicyFrontierService(
        _Policy(mutations=(object(), object()))
    )
    result = service.expand(
        seed=_candidate(),
        priorities=object(),
        snapshot_resolver=lambda _time: None,
        target_identity="Boss",
    )

    assert result.denominator_proven is True
    assert tuple(row.policy_id for row in result.candidates) == (
        "execute:none",
        "execute:canonical_upgrade",
    )
    assert result.candidates[1].mutation_count == 2


def test_no_execute_mutation_deduplicates_to_baseline_only() -> None:
    result = ExtremeSustainedDPSExecutePolicyFrontierService(_Policy()).expand(
        seed=_candidate(),
        priorities=object(),
        snapshot_resolver=lambda _time: None,
        target_identity="Boss",
    )

    assert result.denominator_proven is True
    assert tuple(row.policy_id for row in result.candidates) == ("execute:none",)


def test_unresolved_execute_policy_fails_closed_without_erasing_baseline() -> None:
    result = ExtremeSustainedDPSExecutePolicyFrontierService(
        _Policy(unresolved=("target health unavailable",))
    ).expand(
        seed=_candidate(),
        priorities=object(),
        snapshot_resolver=lambda _time: None,
        target_identity="Boss",
    )

    assert result.denominator_proven is False
    assert tuple(row.policy_id for row in result.candidates) == (
        "execute:none",
        "execute:unresolved",
    )
    assert "target health unavailable" in result.unresolved
