from types import SimpleNamespace

from minmax.build_candidate_food import (
    enumerate_food_candidates,
    filter_food_candidates_for_resource,
    provisioning_candidate_resources,
)
from minmax.resource_costs import ResourceType
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _ProvisioningRepository:
    def list_names(self):
        return (
            "Clockwork Citrus Filet",
            "Ghastly Eye Bowl",
            "Unmapped Feast",
        )

    def canonical_name(self, name):
        value = str(name or "").strip()
        if value.casefold() == "clockwork citrus":
            return "Clockwork Citrus Filet"
        return value

    def resolve(self, name):
        if name == "Unmapped Feast":
            return [], ["unmapped"]
        return [SimpleNamespace(stat=StatId.MAX_MAGICKA, value=1.0)], []


class _ResourceProvisioningRepository:
    def list_names(self):
        return ("Health Meal", "Magicka Drink", "Stamina Meal", "Hybrid Meal")

    def canonical_name(self, name):
        return str(name or "").strip()

    def resolve(self, name):
        effects = {
            "Health Meal": [SimpleNamespace(stat=StatId.MAX_HEALTH, value=5000.0)],
            "Magicka Drink": [SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=500.0)],
            "Stamina Meal": [SimpleNamespace(stat=StatId.MAX_STAMINA, value=5000.0)],
            "Hybrid Meal": [
                SimpleNamespace(stat=StatId.MAX_HEALTH, value=4000.0),
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=4000.0),
            ],
        }
        return effects.get(name, []), []


class _DirectionalProvisioningRepository:
    def list_names(self):
        return (
            "Worse Pool",
            "Equal Sustain",
            "Better Pool",
            "Better Recovery",
            "Mixed Tradeoff",
            "Health Only",
        )

    def canonical_name(self, name):
        return str(name or "").strip()

    def resolve(self, name):
        effects = {
            "Baseline": [
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=3000.0),
                SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=300.0),
            ],
            "Worse Pool": [
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=2500.0),
                SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=300.0),
            ],
            "Equal Sustain": [
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=3000.0),
                SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=300.0),
            ],
            "Better Pool": [
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=3500.0),
                SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=300.0),
            ],
            "Better Recovery": [
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=3000.0),
                SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=450.0),
            ],
            "Mixed Tradeoff": [
                SimpleNamespace(stat=StatId.MAX_MAGICKA, value=2500.0),
                SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=500.0),
            ],
            "Health Only": [SimpleNamespace(stat=StatId.MAX_HEALTH, value=5000.0)],
        }
        return effects.get(name, []), []


class _UnresolvedBaselineProvisioningRepository(_DirectionalProvisioningRepository):
    def resolve(self, name):
        if name == "Baseline":
            return [], ["baseline unresolved"]
        return super().resolve(name)


class _EquivalentProvisioningRepository:
    def __init__(self, *, distinct_tooltips: bool) -> None:
        self.distinct_tooltips = distinct_tooltips

    def list_names(self):
        return ("Alpha Drink", "Beta Drink")

    def canonical_name(self, name):
        return str(name or "").strip()

    def resolve(self, name):
        return [SimpleNamespace(stat=StatId.MAGICKA_RECOVERY, value=500.0)], []

    def description(self, name):
        if self.distinct_tooltips and name == "Beta Drink":
            return "Increase Magicka Recovery by 500. Also does something else."
        return "Increase Magicka Recovery by 500."


def test_food_candidates_use_only_resolved_canonical_foods() -> None:
    baseline = PlayerBuild(Name="Magrat", BuildName="DF Healer", Food="clockwork citrus")

    candidates = enumerate_food_candidates(
        baseline_build=baseline,
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=_ProvisioningRepository(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_id == "DF Healer:food:ghastly-eye-bowl"
    assert candidate.changes[0].path == "Food"
    assert candidate.changes[0].before == "Clockwork Citrus Filet"
    assert candidate.changes[0].after == "Ghastly Eye Bowl"
    assert candidate.candidate_build.Food == "Ghastly Eye Bowl"
    assert baseline.Food == "clockwork citrus"


def test_food_candidate_ids_are_deterministic() -> None:
    kwargs = dict(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Clockwork Citrus Filet"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=_ProvisioningRepository(),
    )

    first = enumerate_food_candidates(**kwargs)
    second = enumerate_food_candidates(**kwargs)

    assert tuple(candidate.candidate_id for candidate in first) == tuple(
        candidate.candidate_id for candidate in second
    )


def test_provisioning_candidates_are_classified_by_resolved_resource_stats() -> None:
    repo = _ResourceProvisioningRepository()
    candidates = enumerate_food_candidates(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Baseline"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=repo,
    )
    by_name = {candidate.candidate_build.Food: candidate for candidate in candidates}

    assert provisioning_candidate_resources(by_name["Health Meal"], repo) == (
        ResourceType.HEALTH,
    )
    assert provisioning_candidate_resources(by_name["Magicka Drink"], repo) == (
        ResourceType.MAGICKA,
    )
    assert provisioning_candidate_resources(by_name["Stamina Meal"], repo) == (
        ResourceType.STAMINA,
    )
    assert provisioning_candidate_resources(by_name["Hybrid Meal"], repo) == (
        ResourceType.HEALTH,
        ResourceType.MAGICKA,
    )


def test_magicka_filter_keeps_magicka_and_mixed_candidates_only() -> None:
    repo = _ResourceProvisioningRepository()
    candidates = enumerate_food_candidates(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Baseline"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=repo,
    )

    filtered = filter_food_candidates_for_resource(
        candidates,
        resource=ResourceType.MAGICKA,
        provisioning_repository=repo,
    )

    assert {candidate.candidate_build.Food for candidate in filtered} == {
        "Hybrid Meal",
        "Magicka Drink",
    }


def test_magicka_filter_prunes_candidates_that_cannot_improve_failed_sustain() -> None:
    repo = _DirectionalProvisioningRepository()
    candidates = enumerate_food_candidates(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Baseline"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=repo,
    )

    filtered = filter_food_candidates_for_resource(
        candidates,
        resource=ResourceType.MAGICKA,
        provisioning_repository=repo,
    )

    assert {candidate.candidate_build.Food for candidate in filtered} == {
        "Better Pool",
        "Better Recovery",
        "Mixed Tradeoff",
    }


def test_magicka_filter_fails_open_when_baseline_effects_are_unresolved() -> None:
    repo = _UnresolvedBaselineProvisioningRepository()
    candidates = enumerate_food_candidates(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Baseline"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=repo,
    )

    filtered = filter_food_candidates_for_resource(
        candidates,
        resource=ResourceType.MAGICKA,
        provisioning_repository=repo,
    )

    assert {candidate.candidate_build.Food for candidate in filtered} == {
        "Worse Pool",
        "Equal Sustain",
        "Better Pool",
        "Better Recovery",
        "Mixed Tradeoff",
    }


def test_exact_equivalent_provisioning_candidates_are_evaluated_once() -> None:
    repo = _EquivalentProvisioningRepository(distinct_tooltips=False)

    candidates = enumerate_food_candidates(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Baseline"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=repo,
    )

    assert tuple(candidate.candidate_build.Food for candidate in candidates) == ("Alpha Drink",)


def test_same_static_effects_with_distinct_tooltips_remain_separate_candidates() -> None:
    repo = _EquivalentProvisioningRepository(distinct_tooltips=True)

    candidates = enumerate_food_candidates(
        baseline_build=PlayerBuild(BuildName="DF Healer", Food="Baseline"),
        character_id="magrat",
        baseline_build_id="DF Healer",
        provisioning_repository=repo,
    )

    assert tuple(candidate.candidate_build.Food for candidate in candidates) == (
        "Alpha Drink",
        "Beta Drink",
    )
