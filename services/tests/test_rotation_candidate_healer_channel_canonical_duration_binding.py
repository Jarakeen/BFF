from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerChannelHealSeed,
)
from services.rotation_healer_channel_runtime_evidence_service import (
    RotationHealerReviewedChannelObservation,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelMagnitudePolicy,
)
from services.rotation_skill_timing_evidence_service import RotationSkillTimingEvidence


_DEMAND = RotationDemandWindow(
    name="canonical channel duration",
    start_seconds=0.0,
    end_seconds=10.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=1,
)


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="canonical-channel-duration",
        plan=RotationPlan(
            character_name="Healer",
            build_name="Channel Build",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _ActionHealingService:
    def project(self, **kwargs):
        return RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(),
            delayed_seeds=(),
            channel_seeds=(
                RotationHealerChannelHealSeed(
                    time_seconds=1.0,
                    sequence=2,
                    source_name="Healing Channel",
                    coefficient_number=1,
                    modeled_heal=150.0,
                ),
            ),
            unresolved=(),
        )


class _SkillTimingService:
    def __init__(self):
        self.calls = []

    def resolve_skill(self, skill_id):
        self.calls.append(skill_id)
        return SimpleNamespace(
            evidence=RotationSkillTimingEvidence(
                skill_id="healing_channel",
                ability_id=123,
                name="Healing Channel",
                cast_time_seconds=0.0,
                channel_time_seconds=2.5,
                is_channeled=True,
                source="canonical ability table ability_id=123",
            ),
            unresolved=(),
        )


def test_provider_joins_canonical_channel_duration_with_reviewed_tick_cadence():
    timing = _SkillTimingService()
    provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=_ActionHealingService(),
        skill_timing_service=timing,
        reviewed_channel_observations=(
            RotationHealerReviewedChannelObservation(
                source_name="Healing Channel",
                coefficient_number=1,
                tick_interval_seconds=1.0,
                first_tick_offset_seconds=0.5,
                tick_on_channel_end_boundary=True,
                magnitude_policy=RotationHealerChannelMagnitudePolicy.SNAPSHOT_AT_CAST,
                provenance=("reviewed cadence fixture",),
            ),
        ),
    )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
    )

    assert timing.calls == ["Healing Channel"]
    assert [event.time_seconds for event in evidence.channel_events] == [1.5, 2.5, 3.5]
    assert [event.modeled_heal for event in evidence.channel_events] == [150.0, 150.0, 150.0]
    assert evidence.modeled_channel_healing == pytest.approx(450.0)
    assert evidence.unresolved == ()


def test_provider_fails_closed_when_reviewed_channel_cadence_is_missing():
    provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=_ActionHealingService(),
        skill_timing_service=_SkillTimingService(),
    )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
    )

    assert evidence.channel_events == ()
    assert evidence.modeled_channel_healing == pytest.approx(0.0)
    assert any(
        "reviewed channel-heal cadence evidence unavailable" in item
        for item in evidence.unresolved
    )
