from types import SimpleNamespace

from minmax.build_candidate_food import enumerate_food_candidates
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
        return [SimpleNamespace(stat="mapped", value=1.0)], []


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
