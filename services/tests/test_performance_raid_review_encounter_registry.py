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
    def __init__(
        self,
        key,
        display_name,
        review_level="baseline",
        *,
        trial_key="test_trial",
        trial_display_name="Test Trial",
        boss_order=1,
    ):
        self.key = key
        self.display_name = display_name
        self.review_level = review_level
        self.trial_key = trial_key
        self.trial_display_name = trial_display_name
        self.boss_order = boss_order

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
    assert adapter.trial_key == "sunspire"
    assert adapter.trial_display_name == "Sunspire"
    assert adapter.boss_order == 1
    assert adapter.list_fights("ABC123") == ("fight-choice",)
    assert adapter.review_report("ABC123", [3, 4]) == "review-result"
    assert runner.calls == [
        ("list", "ABC123"),
        ("review", "ABC123", (3, 4)),
    ]


def test_xalvakka_adapter_is_rockgrove_third_main_boss() -> None:
    runner = _NamedRunner()
    adapter = XalvakkaRaidReviewEncounterAdapter(runner)

    assert adapter.key == "xalvakka"
    assert adapter.display_name == "Xalvakka"
    assert adapter.review_level == "baseline"
    assert adapter.trial_key == "rockgrove"
    assert adapter.trial_display_name == "Rockgrove"
    assert adapter.boss_order == 3
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


def test_registry_rejects_invalid_adapter_metadata() -> None:
    registry = RaidReviewEncounterRegistry((_Adapter("lokke", "Lokkestiiz"),))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_Adapter("LOKKE", "Duplicate"))

    with pytest.raises(ValueError, match="non-empty key"):
        registry.register(_Adapter("", "Missing"))

    with pytest.raises(ValueError, match="review_level"):
        registry.register(_Adapter("mystery", "Mystery", "pretend_complete"))

    with pytest.raises(ValueError, match="trial metadata"):
        registry.register(_Adapter("notrial", "No Trial", trial_key=""))

    with pytest.raises(ValueError, match="boss_order"):
        registry.register(_Adapter("badorder", "Bad Order", boss_order=0))


def test_registry_orders_by_trial_then_boss_order() -> None:
    registry = RaidReviewEncounterRegistry((
        _Adapter("trial_b_second", "Second", trial_key="trial_b", trial_display_name="Trial B", boss_order=2),
        _Adapter("trial_a_third", "Third", trial_key="trial_a", trial_display_name="Trial A", boss_order=3),
        _Adapter("trial_a_first", "First", trial_key="trial_a", trial_display_name="Trial A", boss_order=1),
    ))

    assert [adapter.key for adapter in registry.available()] == [
        "trial_a_first",
        "trial_a_third",
        "trial_b_second",
    ]


def test_default_registry_exposes_trial_and_maturity_metadata() -> None:
    available = RaidReviewEncounterRegistry.default().available()

    assert [
        (
            adapter.key,
            adapter.trial_key,
            adapter.boss_order,
            adapter.review_level,
        )
        for adapter in available
    ] == [
        ("xalvakka", "rockgrove", 3, "baseline"),
        ("lokkestiiz", "sunspire", 1, "mechanic_enriched"),
    ]


def test_unknown_encounter_fails_closed() -> None:
    registry = RaidReviewEncounterRegistry()

    with pytest.raises(KeyError, match="is not supported"):
        registry.get("missing")
