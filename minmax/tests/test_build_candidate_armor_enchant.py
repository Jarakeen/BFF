from models.build_model import PlayerBuild

from minmax.build_candidate_armor_enchant import (
    MODELED_ARMOR_ENCHANTS,
    enumerate_armor_enchant_candidates,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    build.Armor["Chest"].update(
        {
            "Set": "Spell Power Cure",
            "Weight": "Light",
            "Trait": "Divines",
            "Enchant": "Max Magicka",
            "EnchantTier": "Truly Superb",
            "Quality": "Gold",
            "Level": "CP160",
        }
    )
    build.Armor["Hands"].update(
        {
            "Set": "Pillager's Profit",
            "Weight": "Light",
            "Trait": "Divines",
            "Enchant": "Max Health",
            "EnchantTier": "Superb",
            "Quality": "Gold",
            "Level": "CP160",
        }
    )
    return build


def test_armor_enchant_candidates_change_exactly_one_verified_slot() -> None:
    baseline = _build()

    candidates = enumerate_armor_enchant_candidates(
        baseline_build=baseline,
        character_id="magrat",
        baseline_build_id="df-healer",
    )

    assert len(candidates) == len(MODELED_ARMOR_ENCHANTS) - 1
    assert baseline.Armor["Chest"]["Enchant"] == "Max Magicka"
    assert baseline.Armor["Hands"]["Enchant"] == "Max Health"

    first = candidates[0]
    assert len(first.changes) == 1
    assert first.changes[0].path == "Armor.Chest.Enchant"
    assert first.changes[0].before == "Max Magicka"
    assert first.candidate_build.Armor["Hands"]["Enchant"] == "Max Health"


def test_armor_enchant_candidates_require_verified_cp160_truly_superb_scaling() -> None:
    candidates = enumerate_armor_enchant_candidates(
        baseline_build=_build(),
        character_id="magrat",
        baseline_build_id="df-healer",
    )

    assert all("hands" not in candidate.candidate_id.casefold() for candidate in candidates)


def test_armor_enchant_candidate_ids_are_deterministic_and_unique() -> None:
    kwargs = dict(
        baseline_build=_build(),
        character_id="magrat",
        baseline_build_id="DF Healer",
    )
    first = enumerate_armor_enchant_candidates(**kwargs)
    second = enumerate_armor_enchant_candidates(**kwargs)

    first_ids = tuple(candidate.candidate_id for candidate in first)
    assert first_ids == tuple(candidate.candidate_id for candidate in second)
    assert len(first_ids) == len(set(first_ids))
    assert "DF Healer:armor-enchant:chest:max-health" in first_ids
