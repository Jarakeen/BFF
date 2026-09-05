from __future__ import annotations

from services.capability_service import CapabilityService
from models.capability_model import CapabilityProfile


class _FakeClient:

    def __init__(self, fight=None, auras=None):
        self._fight = fight or {"startTime": 0.0, "endTime": 100000.0, "name": "Test Fight"}
        self._auras = auras or []
        self.aura_calls = []

    def get_fight(self, report_code, fight_id):
        return self._fight

    def get_aura_table(self, report_code, fight_id, start_time, end_time, **kwargs):
        self.aura_calls.append(kwargs)
        return self._auras


def test_compute_boss_active_seconds_subtracts_immunity_uptime():

    client = _FakeClient(
        fight={"startTime": 0.0, "endTime": 100000.0, "name": "Test"},
        auras=[{"name": "Damage Shield", "totalUptime": 25000.0}],
    )

    service = CapabilityService(client, reference=None)

    result = service.compute_boss_active_seconds(
        "ABC123", 1, "Damage Shield", "Buff"
    )

    # 100s total fight - 25s immune = 75s active
    assert result == 75.0


def test_compute_boss_active_seconds_queries_enemy_hostility():

    client = _FakeClient(auras=[])

    service = CapabilityService(client, reference=None)

    service.compute_boss_active_seconds("ABC123", 1, "Damage Shield", "Buff")

    assert client.aura_calls[0]["hostility_type"] == "Enemies"
    assert client.aura_calls[0]["data_type"] == "Buffs"


def test_compute_boss_active_seconds_uses_debuffs_data_type_when_requested():

    client = _FakeClient(auras=[])

    service = CapabilityService(client, reference=None)

    service.compute_boss_active_seconds("ABC123", 1, "Vulnerability Marker", "Debuff")

    assert client.aura_calls[0]["data_type"] == "Debuffs"


def test_compute_boss_active_seconds_matches_case_insensitively():

    client = _FakeClient(
        fight={"startTime": 0.0, "endTime": 100000.0},
        auras=[{"name": "damage shield", "totalUptime": 10000.0}],
    )

    service = CapabilityService(client, reference=None)

    result = service.compute_boss_active_seconds("ABC123", 1, "Damage Shield", "Buff")

    assert result == 90.0


def test_compute_boss_active_seconds_returns_none_when_name_is_blank():

    service = CapabilityService(_FakeClient(), reference=None)

    assert service.compute_boss_active_seconds("ABC123", 1, "", "Buff") is None
    assert service.compute_boss_active_seconds("ABC123", 1, "   ", "Buff") is None


def test_compute_boss_active_seconds_returns_full_duration_when_buff_never_seen():
    """
    A name that simply isn't present in this fight's aura list is not
    an error -- some pulls skip the immunity window entirely (e.g. a
    fast burn) -- so this must return the full fight duration, not
    None and not an exception.
    """

    client = _FakeClient(
        fight={"startTime": 0.0, "endTime": 60000.0},
        auras=[{"name": "Unrelated Buff", "totalUptime": 5000.0}],
    )

    service = CapabilityService(client, reference=None)

    result = service.compute_boss_active_seconds("ABC123", 1, "Damage Shield", "Buff")

    assert result == 60.0


def test_compute_boss_active_seconds_sums_multiple_matching_aura_entries():

    client = _FakeClient(
        fight={"startTime": 0.0, "endTime": 100000.0},
        auras=[
            {"name": "Damage Shield", "totalUptime": 10000.0},
            {"name": "Damage Shield", "totalUptime": 15000.0},
        ],
    )

    service = CapabilityService(client, reference=None)

    result = service.compute_boss_active_seconds("ABC123", 1, "Damage Shield", "Buff")

    assert result == 75.0


def test_compute_boss_active_seconds_never_returns_negative():
    """
    If total matched uptime somehow exceeds the fight duration
    (overlapping entries, clock skew in the source data), the result
    is clamped at 0 rather than going negative.
    """

    client = _FakeClient(
        fight={"startTime": 0.0, "endTime": 10000.0},
        auras=[{"name": "Damage Shield", "totalUptime": 50000.0}],
    )

    service = CapabilityService(client, reference=None)

    result = service.compute_boss_active_seconds("ABC123", 1, "Damage Shield", "Buff")

    assert result == 0.0


# --------------------------------------------------
# Model round-trip for the two new fields
# --------------------------------------------------


def test_capability_profile_round_trips_immunity_fields():

    profile = CapabilityProfile(
        Name="Jarakeen",
        ImmunityBuffName="Damage Shield",
        ImmunityBuffKind="Debuff",
    )

    restored = CapabilityProfile.from_dict(profile.to_dict())

    assert restored.ImmunityBuffName == "Damage Shield"
    assert restored.ImmunityBuffKind == "Debuff"


def test_capability_profile_defaults_immunity_kind_to_buff():

    restored = CapabilityProfile.from_dict({"Name": "X"})

    assert restored.ImmunityBuffName == ""
    assert restored.ImmunityBuffKind == "Buff"
