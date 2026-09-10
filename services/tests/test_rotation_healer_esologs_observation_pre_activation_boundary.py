from services.tests.test_rotation_healer_esologs_observation_extractor import (
    _database,
    _event,
    _raw,
    _target,
)
from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationExtractor,
)


def test_pre_activation_heal_within_expiry_tolerance_is_not_used_as_tick(tmp_path):
    events = [
        _event(9990, "hot", tick=True),
        _event(10000, "cast", cast_track=10),
    ]
    events.extend(
        _event(value, "hot", tick=True)
        for value in (11000, 12000, 13000, 14000, 15000, 16000)
    )
    events.append(_event(16020, "damage", source=99, target=99, ability=1))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _raw(tmp_path, events),
        fight_id=4,
        caster_id=7,
        targets=_target(),
    )

    assert len(report.candidates) == 1
    sample = report.candidates[0].sample
    assert sample.activation_time_seconds == 10.0
    assert sample.observed_tick_times_seconds == (
        11.0,
        12.0,
        13.0,
        14.0,
        15.0,
        16.0,
    )
    assert all(
        tick >= sample.activation_time_seconds
        for tick in sample.observed_tick_times_seconds
    )
