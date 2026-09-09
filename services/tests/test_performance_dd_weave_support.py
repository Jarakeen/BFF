from __future__ import annotations

from services.performance_dd_weave_support import (
    _analyze_weave_pairing,
    _decode_cast_event_data,
)


def _event(timestamp: float, ability_id: int, track: int) -> dict:
    return {
        "timestamp": timestamp,
        "abilityGameID": ability_id,
        "castTrackID": track,
        "type": "cast",
    }


def test_weave_pairing_counts_nearest_preceding_light_attacks() -> None:
    names = {
        1: "Light Attack",
        2: "Force Pulse",
        3: "Barbed Trap",
    }
    events = [
        _event(1000, 1, 10),
        _event(1120, 2, 11),
        _event(2000, 1, 12),
        _event(2180, 3, 13),
        _event(3200, 2, 14),
    ]

    result = _analyze_weave_pairing(events, names)

    assert result.LightAttackCasts == 2
    assert result.SkillCasts == 3
    assert result.PairedSkillCasts == 2
    assert result.UnpairedSkillCasts == 1
    assert result.PairingPercent == 66.7
    assert result.MedianPairDelayMs == 150.0
    assert result.EligibleSkillTimestampsMs == (1120.0, 2180.0, 3200.0)


def test_weave_pairing_does_not_reuse_one_light_attack_for_two_skills() -> None:
    names = {1: "Light Attack", 2: "Skill A", 3: "Skill B"}
    events = [
        _event(1000, 1, 1),
        _event(1080, 2, 2),
        _event(1150, 3, 3),
    ]

    result = _analyze_weave_pairing(events, names)

    assert result.PairedSkillCasts == 1
    assert result.SkillCasts == 2
    assert result.PairingPercent == 50.0


def test_weave_pairing_ignores_utility_heavy_attack_and_synergy_casts() -> None:
    names = {
        1: "Light Attack",
        2: "Force Pulse",
        3: "Heavy Attack",
        4: "Bash",
        5: "Use Synergy",
    }
    events = [
        _event(1000, 1, 1),
        _event(1100, 2, 2),
        _event(1400, 3, 3),
        _event(1600, 4, 4),
        _event(1800, 5, 5),
    ]

    result = _analyze_weave_pairing(events, names)

    assert result.LightAttackCasts == 1
    assert result.SkillCasts == 1
    assert result.PairedSkillCasts == 1
    assert result.PairingPercent == 100.0
    assert result.EligibleSkillTimestampsMs == (1100.0,)


def test_weave_pairing_respects_pair_window_and_dedupes_cast_track_id() -> None:
    names = {1: "Light Attack", 2: "Force Pulse"}
    events = [
        _event(1000, 1, 1),
        _event(1000, 1, 1),  # duplicate row for same observed cast
        _event(2401, 2, 2),  # beyond default 1200 ms pairing window
    ]

    result = _analyze_weave_pairing(events, names)

    assert result.LightAttackCasts == 1
    assert result.SkillCasts == 1
    assert result.PairedSkillCasts == 0
    assert result.PairingPercent == 0.0
    assert result.MedianPairDelayMs is None
    assert result.EligibleSkillTimestampsMs == (2401.0,)


def test_decode_cast_event_data_accepts_json_scalar_shape() -> None:
    assert _decode_cast_event_data('[{"type":"cast"}]') == [{"type": "cast"}]
    assert _decode_cast_event_data("nope") == []
