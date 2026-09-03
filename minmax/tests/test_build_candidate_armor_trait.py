from models.build_model import PlayerBuild

from minmax.build_candidate_armor_trait import (
    MODELED_ARMOR_TRAITS,
    enumerate_armor_trait_candidates,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Mundus="The Ritual")
    build.Armor["Head"].update(
        {
            "Set": "Spell Power Cure",
            "Weight": "Light",
            "Trait": "Divines",
            "Enchant": "Max Magicka",
            "Quality": "Gold",
            "Level": "CP160",
        }
    )
    build.Armor["Shoulders"].update(
        {
            "Set": "Symphony of Blades",
            "Weight": "Light",
            "Trait": "Infused",
            "Enchant": "Max Magicka",
            "Quality": "Gold",
            "Level": "CP160",
        }
    )
    return build


def test_armor_trait_candidates_change_exactly_one_equipped_slot() -> None:
    baseline = _build()

    candidates = enumerate_armor_trait_candidates(
        baseline_build=baseline,
        character_id="magrat",
        baseline_build_id="df-healer",
    )

    assert len(candidates) == (len(MODELED_ARMOR_TRAITS) - 1) * 2
    assert baseline.Armor["Head"]["Trait"] == "Divines"
    assert baseline.Armor["Shoulders"]["Trait"] == "Infused"

    first = candidates[0]
    assert len(first.changes) == 1
    assert first.changes[0].path == "Armor.Head.Trait"
    assert first.changes[0].before == "Divines"
    assert first.changes[0].after == "Infused"
    assert first.candidate_build.Armor["Head"]["Trait"] == "Infused"
    assert first.candidate_build.Armor["Shoulders"]["Trait"] == "Infused"


def test_armor_trait_candidates_exclude_unresolved_trait_classes_and_empty_slots() -> None:
    candidates = enumerate_armor_trait_candidates(
        baseline_build=_build(),
        character_id="magrat",
        baseline_build_id="df-healer",
    )

    changed_traits = {candidate.changes[0].after for candidate in candidates}
    assert changed_traits <= set(MODELED_ARMOR_TRAITS)
    assert not {"Sturdy", "Well-Fitted", "Training"} & changed_traits
    assert all("chest" not in candidate.candidate.candidate_id.casefold() for candidate in candidates)


def test_armor_trait_candidate_ids_are_deterministic_and_unique() -> None:
    kwargs = dict(
        baseline_build=_build(),
        character_id="magrat",
        baseline_build_id="DF Healer",
    )

    first = enumerate_armor_trait_candidates(**kwargs)
    second = enumerate_armor_trait_candidates(**kwargs)

    first_ids = tuple(candidate.candidate_id for candidate in first)
    assert first_ids == tuple(candidate.candidate_id for candidate in second)
    assert len(first_ids) == len(set(first_ids))
    assert "DF Healer:armor-trait:head:infused" in first_ids
