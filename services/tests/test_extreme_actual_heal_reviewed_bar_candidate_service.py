from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_actual_heal_reviewed_bar_candidate_service import (
    ExtremeActualHealReviewedBarCandidateService,
)


def _records():
    return [
        {
            "ability_id": 101,
            "base_ability_id": 100,
            "name": "Entropy",
            "skill_line": "Mages Guild",
            "class_type": "",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 0,
        },
        {
            "ability_id": 102,
            "base_ability_id": 100,
            "name": "Degeneration",
            "skill_line": "Mages Guild",
            "class_type": "",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 1,
        },
        {
            "ability_id": 201,
            "base_ability_id": 200,
            "name": "Circle of Protection",
            "skill_line": "Fighters Guild",
            "class_type": "",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 0,
        },
        {
            "ability_id": 301,
            "base_ability_id": 300,
            "name": "Dawnbreaker",
            "skill_line": "Fighters Guild",
            "class_type": "",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 8,
            "morph": 0,
        },
        {
            "ability_id": 401,
            "base_ability_id": 400,
            "name": "Revealing Flare",
            "skill_line": "Support",
            "class_type": "",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 0,
        },
        {
            "ability_id": 501,
            "base_ability_id": 500,
            "name": "Budding Seeds",
            "skill_line": "Green Balance",
            "class_type": "Warden",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 1,
        },
    ]


def _service() -> ExtremeActualHealReviewedBarCandidateService:
    return ExtremeActualHealReviewedBarCandidateService(
        "fake.db",
        skill_loader=lambda _path: _records(),
    )


def test_reviewed_skill_records_are_owned_nonultimate_guild_carriers_only():
    progression = CharacterProgression(
        owned_skill_lines=("Mages Guild", "Fighters Guild", "Support"),
    )

    result = _service().reviewed_skill_records(progression)

    assert [(row["name"], row["skill_line"]) for row in result] == [
        ("Circle of Protection", "Fighters Guild"),
        ("Entropy", "Mages Guild"),
    ]
    assert all(row["name"] != "Dawnbreaker" for row in result)
    assert all(row["name"] != "Revealing Flare" for row in result)
    assert all(row["name"] != "Degeneration" for row in result)


def test_bar_candidates_preserve_scored_heal_and_ultimate_without_duplicate_base_skill():
    progression = CharacterProgression(
        owned_skill_lines=("Mages Guild", "Fighters Guild"),
    )
    baseline = PlayerBuild(
        FrontBarSkills=[
            "Old One",
            "Degeneration",
            "Budding Seeds",
            "Old Four",
            "Old Five",
            "Aggressive Horn",
        ]
    )

    candidates = _service().build_candidates(
        baseline,
        progression,
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="budding_seeds",
        active_bar="front",
    )

    assert candidates
    assert baseline.FrontBarSkills == [
        "Old One",
        "Degeneration",
        "Budding Seeds",
        "Old Four",
        "Old Five",
        "Aggressive Horn",
    ]
    assert all(candidate.candidate_build.FrontBarSkills[2] == "Budding Seeds" for candidate in candidates)
    assert all(candidate.candidate_build.FrontBarSkills[5] == "Aggressive Horn" for candidate in candidates)
    assert all(candidate.changes[0].path != "FrontBarSkills[2]" for candidate in candidates)

    # Entropy is the same base skill as already-slotted Degeneration. The bounded
    # line-count search must not slot a duplicate or perform a passive-equivalent
    # morph swap merely to manufacture another candidate.
    assert all("Entropy" not in candidate.candidate_build.FrontBarSkills for candidate in candidates)

    circle_candidates = [
        candidate
        for candidate in candidates
        if "Circle of Protection" in candidate.candidate_build.FrontBarSkills
    ]
    assert circle_candidates
    assert all(
        candidate.changes[0].after["reviewed_passive"] == "Slayer"
        for candidate in circle_candidates
    )


def test_bar_candidate_generation_fails_closed_when_scored_heal_is_not_on_active_bar():
    progression = CharacterProgression(owned_skill_lines=("Mages Guild",))
    baseline = PlayerBuild(
        FrontBarSkills=["A", "B", "C", "D", "E", "Ultimate"],
    )

    assert _service().build_candidates(
        baseline,
        progression,
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="budding_seeds",
        active_bar="front",
    ) == ()
