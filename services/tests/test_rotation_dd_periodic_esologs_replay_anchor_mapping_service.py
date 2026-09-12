from __future__ import annotations

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
)
from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsCastImpactObservation,
)
from services.rotation_dd_periodic_esologs_replay_anchor_mapping_service import (
    RotationDDPeriodicEsoLogsReplayAnchorMappingService,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Parse Test",
        build_name="DD",
        duration_seconds=20.0,
        actions=tuple(actions),
    )


def _observation(
    *,
    cast_timestamp_ms: float = 2000.0,
    impact_timestamp_ms: float = 2150.0,
    cast_track_linked: bool = True,
    cast_event_index: int = 10,
    impact_event_index: int = 11,
) -> RotationDDPeriodicEsoLogsCastImpactObservation:
    return RotationDDPeriodicEsoLogsCastImpactObservation(
        skill_entity_id="stampede",
        report_code="R",
        fight_id=1,
        source_id=42,
        cast_event_index=cast_event_index,
        cast_timestamp_ms=cast_timestamp_ms,
        cast_ability_id=39807,
        impact_event_index=impact_event_index,
        impact_timestamp_ms=impact_timestamp_ms,
        impact_ability_id=38792,
        cast_track_id=77,
        cast_track_linked=cast_track_linked,
    )


def test_maps_exact_linked_observation_to_semantic_impact_evidence() -> None:
    plan = _plan(
        RotationAction(
            time_seconds=1.0,
            sequence=7,
            kind=RotationActionKind.SKILL,
            name="Stampede",
            bar="back",
        )
    )

    result = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(_observation(),),
        replay_origin_timestamp_ms=1000.0,
    )

    assert result.unresolved == ()
    assert len(result.evidence) == 1
    evidence = result.evidence[0]
    assert evidence.skill_entity_id == "stampede"
    assert evidence.action_time_seconds == pytest.approx(1.0)
    assert evidence.action_sequence == 7
    assert evidence.activation_anchor is PeriodicDamageActivationAnchor.IMPACT
    assert evidence.anchor_time_seconds == pytest.approx(1.15)
    assert "report R fight 1 source 42" in evidence.source
    assert "cast event 10 impact event 11" in evidence.source


def test_does_not_use_nearest_rotation_action_for_observed_cast() -> None:
    plan = _plan(
        RotationAction(
            time_seconds=1.0,
            sequence=7,
            kind=RotationActionKind.SKILL,
            name="Stampede",
            bar="back",
        )
    )

    result = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(_observation(cast_timestamp_ms=2010.0, impact_timestamp_ms=2160.0),),
        replay_origin_timestamp_ms=1000.0,
    )

    assert result.evidence == ()
    assert any("no exact stampede rotation action exists at 1.01s" in item for item in result.unresolved)


def test_unlinked_fallback_correlation_remains_observational() -> None:
    plan = _plan(
        RotationAction(
            time_seconds=1.0,
            sequence=7,
            kind=RotationActionKind.SKILL,
            name="Stampede",
            bar="back",
        )
    )

    result = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(_observation(cast_track_linked=False),),
        replay_origin_timestamp_ms=1000.0,
    )

    assert result.evidence == ()
    assert any("not cast-track-linked" in item for item in result.unresolved)


def test_ambiguous_same_time_same_skill_actions_fail_closed() -> None:
    plan = _plan(
        RotationAction(
            time_seconds=1.0,
            sequence=7,
            kind=RotationActionKind.SKILL,
            name="Stampede",
            bar="back",
        ),
        RotationAction(
            time_seconds=1.0,
            sequence=8,
            kind=RotationActionKind.SKILL,
            name="Stampede",
            bar="back",
        ),
    )

    result = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(_observation(),),
        replay_origin_timestamp_ms=1000.0,
    )

    assert result.evidence == ()
    assert any("2 exact stampede rotation actions exist at 1s" in item for item in result.unresolved)


def test_conflicting_observations_for_same_action_fail_closed() -> None:
    plan = _plan(
        RotationAction(
            time_seconds=1.0,
            sequence=7,
            kind=RotationActionKind.SKILL,
            name="Stampede",
            bar="back",
        )
    )

    result = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(
            _observation(),
            _observation(
                impact_timestamp_ms=2200.0,
                cast_event_index=12,
                impact_event_index=13,
            ),
        ),
        replay_origin_timestamp_ms=1000.0,
    )

    assert result.evidence == ()
    assert any("conflicting exact impact observations" in item for item in result.unresolved)


def test_replay_origin_must_be_valid() -> None:
    with pytest.raises(ValueError, match="replay origin timestamp"):
        RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
            plan=_plan(),
            observations=(),
            replay_origin_timestamp_ms=float("nan"),
        )
