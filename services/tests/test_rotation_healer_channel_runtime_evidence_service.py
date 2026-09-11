from services.rotation_healer_channel_runtime_evidence_service import (
    RotationHealerChannelRuntimeEvidenceService,
    RotationHealerReviewedChannelObservation,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelMagnitudePolicy,
)
from services.rotation_skill_timing_evidence_service import RotationSkillTimingEvidence


def _timing(*, is_channeled=True, channel_time_seconds=3.0):
    return RotationSkillTimingEvidence(
        skill_id="healing_channel",
        ability_id=123,
        name="Healing Channel",
        cast_time_seconds=0.0,
        channel_time_seconds=channel_time_seconds,
        is_channeled=is_channeled,
        source="canonical ability table ability_id=123",
    )


def _observation():
    return RotationHealerReviewedChannelObservation(
        source_name="Healing Channel",
        coefficient_number=1,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_channel_end_boundary=True,
        magnitude_policy=RotationHealerChannelMagnitudePolicy.RECALCULATE_EACH_TICK,
        provenance=("reviewed combat-log cadence",),
    )


def test_channel_runtime_evidence_uses_canonical_duration_and_reviewed_cadence():
    result = RotationHealerChannelRuntimeEvidenceService().resolve(
        timing=_timing(channel_time_seconds=3.2),
        observation=_observation(),
        source_name="Healing Channel",
        coefficient_number=1,
    )

    assert result.unresolved == ()
    assert result.runtime_evidence is not None
    evidence = result.runtime_evidence
    assert evidence.channel_duration_seconds == 3.2
    assert evidence.tick_interval_seconds == 1.0
    assert evidence.first_tick_offset_seconds == 1.0
    assert evidence.tick_on_channel_end_boundary is True
    assert evidence.magnitude_policy is RotationHealerChannelMagnitudePolicy.RECALCULATE_EACH_TICK
    assert evidence.provenance == (
        "canonical ability table ability_id=123",
        "reviewed combat-log cadence",
    )


def test_channel_runtime_evidence_requires_canonical_channeled_identity():
    result = RotationHealerChannelRuntimeEvidenceService().resolve(
        timing=_timing(is_channeled=False),
        observation=_observation(),
        source_name="Healing Channel",
        coefficient_number=1,
    )

    assert result.runtime_evidence is None
    assert result.unresolved == (
        "Healing Channel coefficient 1: canonical skill timing is not channeled",
    )


def test_channel_runtime_evidence_requires_canonical_duration():
    result = RotationHealerChannelRuntimeEvidenceService().resolve(
        timing=_timing(channel_time_seconds=None),
        observation=_observation(),
        source_name="Healing Channel",
        coefficient_number=1,
    )

    assert result.runtime_evidence is None
    assert result.unresolved == (
        "Healing Channel coefficient 1: canonical channel duration is unavailable",
    )


def test_channel_runtime_evidence_requires_reviewed_cadence():
    result = RotationHealerChannelRuntimeEvidenceService().resolve(
        timing=_timing(),
        observation=None,
        source_name="Healing Channel",
        coefficient_number=1,
    )

    assert result.runtime_evidence is None
    assert result.unresolved == (
        "Healing Channel coefficient 1: reviewed channel-heal cadence evidence unavailable",
    )
