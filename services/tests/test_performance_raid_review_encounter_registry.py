from __future__ import annotations

import pytest

from services.performance_raid_review_encounter_registry import (
    LokkestiizRaidReviewEncounterAdapter,
    RaidReviewEncounterRegistry,
    XalvakkaRaidReviewEncounterAdapter,
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


class _NamedRunner:
    def __init__(self):
        self.calls = []

    def list_fights(self, report_code):
        self.calls.append(("list", report_code))
        return ("named-fight-choice",)

    def review_report(self, report_code, fight_ids):
        self.calls.append(("review", report_code, tuple(fight_ids)))
        return "named-review-result"


class _Adapter:
    def __init__(self, key, display_name, review_level="baseline"):
        self.key = key
        self.display_name = display_name
        self.review_level = review_level

    def list_fights(self, report_code):
        return ()

    def review_report(self, report_code, fight_ids):
        return None


def test_lokkestiiz_adapter_delegates_to_existing_runner() -> None:
    runner = _Runner()
    adapter = LokkestiizRaidReviewEncounterAdapter(runner)

    assert adapter.key == "lokkestiiz"
    assert adapter.display_name == "Lokkestiiz"
    assert adapter.review_level == "mechanic_enriched"
    assert adapter.list_fights("ABC123") == ("fight-choice",)
    assert adapter.review_report("ABC123", [3, 4]) == "review-result"
    assert runner.calls == [
        ("list", "ABC123"),
        ("review", "ABC123", (3, 4)),
    ]


def test_xalvakka_adapter_delegates_to_named_boss_baseline_runner() -> None:
    runner = _NamedRunner()
    adapter = XalvakkaRaidReviewEncounterAdapter(runner)

    assert adapter.key == "xalvakka"
    assert adapter.display_name == "Xalvakka"
    assert adapter.review_level == "baseline"
    assert adapter.list_fights("ABC123") == ("named-fight-choice",)
    assert adapter.review_report("ABC123", [8, 9]) == "named-review-result"
    assert runner.calls == [
        ("list", "ABC123"),
        ("review", "ABC123", (8, 9)),
    ]


def test_registry_resolves_keys_case_insensitively() -> None:
    adapter = _Adapter("lokkestiiz", "Lokkestiiz")
    registry = RaidReviewEncounterRegistry((adapter,))

    assert registry.get("LOKKESTIIZ") is adapter


def test_registry_rejects_duplicate_empty_or_unknown_maturity() -> None:
    registry = RaidReviewEncounterRegistry((_Adapter("lokke", "Lokkestiiz"),))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_Adapter("LOKKE", "Duplicate"))

    with pytest.raises(ValueError, match="non-empty key"):
        registry.register(_Adapter("", "Missing"))

    with pytest.raises(ValueError, match="review_level"):
        registry.register(_Adapter("mystery", "Mystery", "pretend_complete"))


def test_registry_lists_supported_encounters_deterministically() -> None:
    registry = RaidReviewEncounterRegistry((
        _Adapter("zeta", "Zeta"),
        _Adapter("alpha", "Alpha"),
    ))

    assert [adapter.key for adapter in registry.available()] == ["alpha", "zeta"]


def test_default_registry_exposes_lokke_enriched_and_xalvakka_baseline() -> None:
    available = RaidReviewEncounterRegistry.default().available()

    assert [(adapter.key, adapter.review_level) for adapter in available] == [
        ("lokkestiiz", "mechanic_enriched"),
        ("xalvakka", "baseline"),
    ]


def test_unknown_encounter_fails_closed() -> None:
    registry = RaidReviewEncounterRegistry()

    with pytest.raises(KeyError, match="is not supported"):
        registry.get("missing")
