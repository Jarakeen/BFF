from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadencePlanCandidate,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodObligation,
    RotationSupportCadenceNeighborhoodService,
)
from services.rotation_support_refresh_cadence_service import (
    RotationSupportRefreshCadenceCandidate,
    RotationSupportRefreshCadenceResult,
)


@dataclass
class _MaterializeCall:
    seed_plan: RotationPlan
    cadence_result: RotationSupportRefreshCadenceResult
    priorities: object
    source_bar: str | None


class _RecordingMaterializer:
    def __init__(self, by_effect: dict[str, tuple[RotationSupportCadencePlanCandidate, ...]]) -> None:
        self.by_effect = by_effect
        self.calls: list[_MaterializeCall] = []

    def materialize(self, *, seed_plan, cadence_result, priorities=None, source_bar=None):
        self.calls.append(
            _MaterializeCall(
                seed_plan=seed_plan,
                cadence_result=cadence_result,
                priorities=priorities,
                source_bar=source_bar,
            )
        )
        return self.by_effect.get(cadence_result.effect_key, ())


def _seed() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Energy Orb", "back"),
        ),
    )


def _cadence_result(effect_key: str, skill_id: str, *, unresolved=()):
    return RotationSupportRefreshCadenceResult(
        effect_key=effect_key,
        source_skill_id=skill_id,
        candidates=(),
        unresolved=tuple(unresolved),
    )


def _candidate(candidate_id: str, effect_key: str, skill_id: str) -> RotationSupportCadencePlanCandidate:
    cadence = RotationSupportRefreshCadenceCandidate(
        candidate_key=candidate_id.rsplit(":", 1)[-1],
        effect_key=effect_key,
        source_skill_id=skill_id,
        recast_interval_seconds=10.0,
        projected_steady_state_uptime_ratio=1.0,
        effective_duration_seconds=10.0,
        target_ratio=0.9,
        rationale=f"rationale for {candidate_id}",
    )
    return RotationSupportCadencePlanCandidate(
        candidate_id=candidate_id,
        effect_key=effect_key,
        source_skill_id=skill_id,
        cadence=cadence,
        refresh_policy=object(),  # type: ignore[arg-type]
        refinement=type("Refinement", (), {"plan": _seed()})(),  # type: ignore[arg-type]
    )


def test_generates_one_change_neighborhood_from_same_seed_plan() -> None:
    seed = _seed()
    prayer_full = _candidate(
        "minor_berserk:combat_prayer:full_coverage",
        "minor_berserk",
        "combat_prayer",
    )
    prayer_floor = _candidate(
        "minor_berserk:combat_prayer:target_floor",
        "minor_berserk",
        "combat_prayer",
    )
    orb_full = _candidate(
        "undaunted_orb:energy_orb:full_coverage",
        "undaunted_orb",
        "energy_orb",
    )
    materializer = _RecordingMaterializer(
        {
            "minor_berserk": (prayer_full, prayer_floor),
            "undaunted_orb": (orb_full,),
        }
    )
    service = RotationSupportCadenceNeighborhoodService(materializer)

    result = service.generate(
        seed_plan=seed,
        obligations=(
            RotationSupportCadenceNeighborhoodObligation(
                _cadence_result("minor_berserk", "combat_prayer"),
                source_bar="front",
            ),
            RotationSupportCadenceNeighborhoodObligation(
                _cadence_result("undaunted_orb", "energy_orb"),
                source_bar="back",
            ),
        ),
        priorities="priority evidence",  # type: ignore[arg-type]
    )

    assert result.seed_plan is seed
    assert result.candidates == (prayer_full, prayer_floor, orb_full)
    assert len(materializer.calls) == 2
    assert all(call.seed_plan is seed for call in materializer.calls)
    assert [call.source_bar for call in materializer.calls] == ["front", "back"]
    assert all(call.priorities == "priority evidence" for call in materializer.calls)


def test_does_not_form_cartesian_products_across_obligations() -> None:
    first = (
        _candidate("a:skill_a:full_coverage", "a", "skill_a"),
        _candidate("a:skill_a:target_floor", "a", "skill_a"),
    )
    second = (
        _candidate("b:skill_b:full_coverage", "b", "skill_b"),
        _candidate("b:skill_b:target_floor", "b", "skill_b"),
    )
    materializer = _RecordingMaterializer({"a": first, "b": second})

    result = RotationSupportCadenceNeighborhoodService(materializer).generate(
        seed_plan=_seed(),
        obligations=(
            RotationSupportCadenceNeighborhoodObligation(_cadence_result("a", "skill_a")),
            RotationSupportCadenceNeighborhoodObligation(_cadence_result("b", "skill_b")),
        ),
    )

    assert len(result.candidates) == 4
    assert [candidate.candidate_id for candidate in result.candidates] == [
        "a:skill_a:full_coverage",
        "a:skill_a:target_floor",
        "b:skill_b:full_coverage",
        "b:skill_b:target_floor",
    ]


def test_unresolved_cadence_family_is_preserved_even_without_candidates() -> None:
    unresolved = _cadence_result(
        "major_slayer",
        "pillagers_profit",
        unresolved=("cycle evidence required", "cycle evidence required"),
    )
    materializer = _RecordingMaterializer({})

    result = RotationSupportCadenceNeighborhoodService(materializer).generate(
        seed_plan=_seed(),
        obligations=(RotationSupportCadenceNeighborhoodObligation(unresolved),),
    )

    assert result.candidates == ()
    assert result.unresolved == (
        "major_slayer:pillagers_profit: cycle evidence required",
    )


def test_duplicate_candidate_ids_across_families_are_rejected() -> None:
    duplicate = _candidate("same:id:full_coverage", "a", "skill_a")
    materializer = _RecordingMaterializer({"a": (duplicate,), "b": (duplicate,)})

    with pytest.raises(ValueError, match="duplicate support cadence neighborhood candidate_id"):
        RotationSupportCadenceNeighborhoodService(materializer).generate(
            seed_plan=_seed(),
            obligations=(
                RotationSupportCadenceNeighborhoodObligation(_cadence_result("a", "skill_a")),
                RotationSupportCadenceNeighborhoodObligation(_cadence_result("b", "skill_b")),
            ),
        )


def test_source_bar_is_normalized_and_invalid_values_are_rejected() -> None:
    obligation = RotationSupportCadenceNeighborhoodObligation(
        _cadence_result("a", "skill_a"),
        source_bar=" FRONT ",
    )
    assert obligation.source_bar == "front"

    with pytest.raises(ValueError, match="source_bar must be front or back"):
        RotationSupportCadenceNeighborhoodObligation(
            _cadence_result("a", "skill_a"),
            source_bar="middle",
        )


def test_empty_obligation_set_returns_empty_neighborhood() -> None:
    seed = _seed()
    materializer = _RecordingMaterializer({})

    result = RotationSupportCadenceNeighborhoodService(materializer).generate(
        seed_plan=seed,
        obligations=(),
    )

    assert result.seed_plan is seed
    assert result.candidates == ()
    assert result.unresolved == ()
    assert materializer.calls == []
