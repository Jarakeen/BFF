from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_horizon_displacement_provenance_quality_service import (
    RotationHorizonDisplacementProvenanceQuality,
    RotationHorizonDisplacementProvenanceQualityService,
)
from services.rotation_priority_displacement_provenance_replay_service import (
    RotationDisplacementQueueInstance,
    RotationDisplacementSpilloverProvenance,
)


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Tester",
        build_name="DD",
        role="DD",
        entries=(
            AbilityPriorityEntry(bar="front", slot=1, skill_name="High", priority=1),
            AbilityPriorityEntry(bar="front", slot=2, skill_name="Mid", priority=2),
            AbilityPriorityEntry(bar="front", slot=3, skill_name="Low", priority=3),
        ),
    )


def _unknown_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Tester",
        build_name="DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(0, 0, RotationActionKind.SKILL, name="High", bar="front"),
        ),
        unresolved=(
            "skill 'Low' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )


def test_multiple_replayed_same_skill_instances_enrich_unknown_as_deduplicated_queue_saturation() -> None:
    provenance = RotationDisplacementSpilloverProvenance(
        skill_name="Low",
        bar="front",
        source_time_seconds=None,
        source_sequence=None,
        last_observed_queue_time_seconds=60.0,
        plausible_instances=(
            RotationDisplacementQueueInstance("Low", "front", 37.0, 1),
            RotationDisplacementQueueInstance("Low", "front", 49.0, 1),
        ),
        unresolved=(
            "multiple same-skill action instances survive in the reconstructed final queue",
        ),
    )

    row = RotationHorizonDisplacementProvenanceQualityService().classify(
        _unknown_plan(),
        priorities=_priorities(),
        spillover_provenance=(provenance,),
    ).rows[0]

    assert (
        row.quality
        is RotationHorizonDisplacementProvenanceQuality.DEDUPLICATED_QUEUE_SATURATION
    )
    assert tuple(item.source_time_seconds for item in row.plausible_instances) == (
        37.0,
        49.0,
    )
    assert "not proof of ordinary cadence debt" in row.reason


def test_single_replayed_instance_does_not_overclaim_missing_displacement_start() -> None:
    provenance = RotationDisplacementSpilloverProvenance(
        skill_name="Low",
        bar="front",
        source_time_seconds=49.0,
        source_sequence=1,
        last_observed_queue_time_seconds=60.0,
        plausible_instances=(
            RotationDisplacementQueueInstance("Low", "front", 49.0, 1),
        ),
    )

    row = RotationHorizonDisplacementProvenanceQualityService().classify(
        _unknown_plan(),
        priorities=_priorities(),
        spillover_provenance=(provenance,),
    ).rows[0]

    assert row.quality is RotationHorizonDisplacementProvenanceQuality.UNKNOWN_PROVENANCE
    assert len(row.plausible_instances) == 1


def test_existing_protected_quality_is_preserved_even_when_provenance_is_available() -> None:
    plan = RotationPlan(
        character_name="Tester",
        build_name="DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(0, 0, RotationActionKind.SKILL, name="High", bar="front"),
            RotationAction(30, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
            RotationAction(45, 0, RotationActionKind.SKILL, name="High", bar="front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 30s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )
    provenance = RotationDisplacementSpilloverProvenance(
        skill_name="High",
        bar="front",
        source_time_seconds=45.0,
        source_sequence=0,
        last_observed_queue_time_seconds=60.0,
        plausible_instances=(
            RotationDisplacementQueueInstance("High", "front", 45.0, 0),
        ),
    )

    row = RotationHorizonDisplacementProvenanceQualityService().classify(
        plan,
        priorities=_priorities(),
        spillover_provenance=(provenance,),
    ).rows[0]

    assert (
        row.quality
        is RotationHorizonDisplacementProvenanceQuality.PROTECTED_OBLIGATION_SATURATION
    )
