from __future__ import annotations

import pytest

from services.performance_raid_review_encounter_registry import (
    LokkestiizRaidReviewEncounterAdapter,
    RaidReviewEncounterRegistry,
)


class _Runner:
    def __init__(self):
        self.calls = []

    def list_lokkestiiz_fights(self, report_code):
        self.calls.append(("list", report_code))
        return ("fight-choice",)

    def review_report(self, report_code, fight_ids):
        self.calls.append(("review", report_code, tuple(fight_ids)))
        return "review-result"


class _Adapter:
    def __init__(self, key, display_name):
        self.key = key
        self.display_name = display_name

    def list_fights(self, report_code):
        return ()

    def review_report(self, report_code, fight_ids):
        return None


def test_lokkestiiz_adapter_delegates_to_existing_runner() -> None:
    runner = _Runner()
    adapter = LokkestiizRaidReviewEncounterAdapter(runner)

    assert adapter.key == "lokkestiiz"
    assert adapter.display_name == "Lokkestiiz"
    assert adapter.list_fights("ABC123") == ("fight-choice",)
    assert adapter.review_report("ABC123", [3, 4]) == "review-result"
    assert runner.calls == [
        ("list", "ABC123"),
        ("review", "ABC123", (3, 4)),
    ]


def test_registry_resolves_keys_case_insensitively() -> None:
    adapter = _Adapter("lokkestiiz", "Lokkestiiz")
    registry = RaidReviewEncounterRegistry((adapter,))

    assert registry.get("LOKKESTIIZ") is adapter


def test_registry_rejects_duplicate_or_empty_keys() -> None:
    registry = RaidReviewEncounterRegistry((_Adapter("lokke", "Lokkestiiz"),))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_Adapter("LOKKE", "Duplicate"))

    with pytest.raises(ValueError, match="non-empty key"):
        registry.register(_Adapter("", "Missing"))


def test_registry_lists_supported_encounters_deterministically() -> None:
    registry = RaidReviewEncounterRegistry((
        _Adapter("zeta", "Zeta"),
        _Adapter("alpha", "Alpha"),
    ))

    assert [adapter.key for adapter in registry.available()] == ["alpha", "zeta"]


def test_unknown_encounter_fails_closed() -> None:
    registry = RaidReviewEncounterRegistry()

    with pytest.raises(KeyError, match="is not supported"):
        registry.get("xalvakka")
