from services.esologs_event_interpreter import SemanticCombatEvent, SemanticEventKind
from services.rotation_encounter_esologs_damage_observation_service import (
    RotationEncounterDamageObservationTarget,
    RotationEncounterEsoLogsDamageObservationService,
)


class _EventSource:
    def __init__(self, events) -> None:
        self.events = tuple(events)
        self.calls = []

    def iter_fight(self, report_code, fight_id, *, event_kinds=None):
        self.calls.append((report_code, fight_id, event_kinds))
        for event in self.events:
            if event_kinds is None or event.event_kind in event_kinds:
                yield event


def _event(
    *,
    index,
    timestamp,
    kind,
    source_id=900,
    target_id=None,
    ability_id=None,
    ability_name=None,
    target_is_friendly=None,
):
    return SemanticCombatEvent(
        report_code="RG",
        fight_id=7,
        event_index=index,
        timestamp=float(timestamp),
        event_kind=kind,
        source_id=source_id,
        target_id=target_id,
        ability_game_id=ability_id,
        extra_ability_game_id=None,
        ability_name=ability_name,
        amount=12000.0 if kind == SemanticEventKind.DAMAGE else None,
        stack=None,
        source_is_friendly=False,
        target_is_friendly=target_is_friendly,
        hit_type=None,
        tick=True if kind == SemanticEventKind.DAMAGE else None,
        cast_track_id=None,
        resource_change=None,
        resource_change_type=None,
        other_resource_change=None,
        max_resource_amount=None,
        waste=None,
        overheal=None,
        absorbed=None,
        raw_event_type="damage" if kind == SemanticEventKind.DAMAGE else "cast",
        raw_event={},
    )


def _target():
    return RotationEncounterDamageObservationTarget(
        canonical_mechanic_id="creeping_manifold",
        cast_ability_names=("Creeping Manifold",),
        damage_ability_game_ids=(777001,),
    )


def test_observation_reports_per_cast_cadence_and_unique_target_scope_without_promoting_policy() -> None:
    source = _EventSource(
        (
            _event(
                index=1,
                timestamp=10000,
                kind=SemanticEventKind.CAST,
                ability_name="Creeping Manifold",
            ),
            _event(index=2, timestamp=10100, kind=SemanticEventKind.DAMAGE, target_id=11, ability_id=777001, target_is_friendly=True),
            _event(index=3, timestamp=10120, kind=SemanticEventKind.DAMAGE, target_id=12, ability_id=777001, target_is_friendly=True),
            _event(index=4, timestamp=10135, kind=SemanticEventKind.DAMAGE, target_id=13, ability_id=777001, target_is_friendly=True),
            _event(index=5, timestamp=11400, kind=SemanticEventKind.DAMAGE, target_id=11, ability_id=777001, target_is_friendly=True),
            _event(index=6, timestamp=11420, kind=SemanticEventKind.DAMAGE, target_id=12, ability_id=777001, target_is_friendly=True),
            _event(index=7, timestamp=11440, kind=SemanticEventKind.DAMAGE, target_id=13, ability_id=777001, target_is_friendly=True),
            _event(
                index=8,
                timestamp=13000,
                kind=SemanticEventKind.CAST,
                ability_name="Creeping Manifold",
            ),
            _event(index=9, timestamp=13100, kind=SemanticEventKind.DAMAGE, target_id=21, ability_id=777001, target_is_friendly=True),
            _event(index=10, timestamp=13125, kind=SemanticEventKind.DAMAGE, target_id=22, ability_id=777001, target_is_friendly=True),
        )
    )
    service = RotationEncounterEsoLogsDamageObservationService(source)

    report = service.observe(
        report_code="RG",
        fight_id=7,
        target=_target(),
        timestamp_scale=0.001,
        recipient_tick_merge_tolerance_seconds=0.05,
    )

    assert report.unresolved == ()
    assert len(report.candidates) == 2

    first = report.candidates[0]
    assert first.canonical_mechanic_id == "creeping_manifold"
    assert first.cast_time_seconds == 10.0
    assert first.logical_damage_tick_times_seconds == (10.1, 11.4)
    assert first.logical_damage_tick_offsets_seconds == (0.1, 1.4)
    assert first.cadence_intervals_seconds == (1.3,)
    assert first.target_ids == (11, 12, 13)
    assert first.observed_target_count == 3
    assert first.raw_damage_event_count == 6
    assert "candidate evidence is not promoted" in first.provenance[-1]

    second = report.candidates[1]
    assert second.cast_time_seconds == 13.0
    assert second.logical_damage_tick_times_seconds == (13.1,)
    assert second.target_ids == (21, 22)
    assert second.observed_target_count == 2


def test_observation_uses_next_matching_cast_as_boundary_without_guessing_episode_gap() -> None:
    source = _EventSource(
        (
            _event(index=1, timestamp=1000, kind=SemanticEventKind.CAST, ability_name="Creeping Manifold"),
            _event(index=2, timestamp=1500, kind=SemanticEventKind.DAMAGE, target_id=1, ability_id=777001, target_is_friendly=True),
            _event(index=3, timestamp=2000, kind=SemanticEventKind.CAST, ability_name="Creeping Manifold"),
            _event(index=4, timestamp=2100, kind=SemanticEventKind.DAMAGE, target_id=2, ability_id=777001, target_is_friendly=True),
        )
    )

    report = RotationEncounterEsoLogsDamageObservationService(source).observe(
        report_code="RG",
        fight_id=7,
        target=_target(),
        timestamp_scale=0.001,
    )

    assert report.candidates[0].target_ids == (1,)
    assert report.candidates[1].target_ids == (2,)


def test_observation_fails_closed_when_explicit_cast_alias_is_absent() -> None:
    source = _EventSource(
        (
            _event(index=1, timestamp=1000, kind=SemanticEventKind.DAMAGE, target_id=1, ability_id=777001, target_is_friendly=True),
        )
    )

    report = RotationEncounterEsoLogsDamageObservationService(source).observe(
        report_code="RG",
        fight_id=7,
        target=_target(),
    )

    assert report.candidates == ()
    assert report.unresolved == (
        "creeping_manifold: no matching cast event across explicit observation aliases",
    )


def test_observation_requires_lower_snake_case_canonical_identity() -> None:
    service = RotationEncounterEsoLogsDamageObservationService(_EventSource(()))
    target = RotationEncounterDamageObservationTarget(
        canonical_mechanic_id="Creeping Manifold",
        cast_ability_names=("Creeping Manifold",),
        damage_ability_names=("Creeping Manifold",),
    )

    try:
        service.observe(report_code="RG", fight_id=7, target=target)
    except ValueError as exc:
        assert "lower_snake_case" in str(exc)
    else:
        raise AssertionError("noncanonical mechanic identity should fail closed")
