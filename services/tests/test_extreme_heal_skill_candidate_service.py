from __future__ import annotations

import sqlite3

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidateService


def _write_fixture(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                class_type TEXT,
                skill_line TEXT,
                is_player INTEGER,
                is_passive INTEGER
            );
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                is_passive INTEGER
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE skill_component_classification (
                skill_rank_id INTEGER,
                coefficient_number INTEGER,
                effect_kind TEXT,
                can_crit INTEGER
            );
            """
        )
        db.executemany(
            "INSERT INTO skill(id, name, is_passive) VALUES (?, ?, ?)",
            (
                (1, "Budding Seeds", 0),
                (2, "Breath of Life", 0),
                (3, "Grand Healing", 0),
                (4, "Blood Altar", 0),
                (5, "Passive Heal Thing", 1),
                (6, "Creature Heal", 0),
            ),
        )
        db.executemany(
            "INSERT INTO ability(ability_id, name, class_type, skill_line, is_player, is_passive) VALUES (?, ?, ?, ?, ?, ?)",
            (
                (101, "Budding Seeds", "Warden", "Green Balance", 1, 0),
                (102, "Budding Seeds", "Warden", "Green Balance", 1, 0),
                (201, "Breath of Life", "Templar", "Restoring Light", 1, 0),
                (301, "Grand Healing", "", "Restoration Staff", 1, 0),
                (401, "Blood Altar", "", "Undaunted", 1, 0),
                (501, "Passive Heal Thing", "", "Restoration Staff", 1, 1),
                (601, "Creature Heal", "", "Restoration Staff", 0, 0)
            ),
        )
        db.executemany(
            "INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph) VALUES (?, ?, ?, ?, ?, ?)",
            (
                (11, 1, 101, "Budding Seeds", 3, 1),
                (12, 1, 102, "Budding Seeds", 4, 1),
                (21, 2, 201, "Breath of Life", 4, 1),
                (31, 3, 301, "Grand Healing", 4, 0),
                (41, 4, 401, "Blood Altar", 4, 0),
                (51, 5, 501, "Passive Heal Thing", 2, 0),
                (61, 6, 601, "Creature Heal", 4, 0)
            ),
        )
        db.executemany(
            "INSERT INTO skill_component_classification(skill_rank_id, coefficient_number, effect_kind, can_crit) VALUES (?, ?, ?, ?)",
            (
                # Deliberately use an obsolete component number on rank 3. The
                # max-rank candidate must not inherit this archaeological debris.
                (11, 9, "heal", 0),
                (12, 1, "heal", 1),
                (12, 2, "heal", 1),
                (21, 1, "heal", 1),
                (31, 1, "heal", 1),
                (41, 1, "heal", 1),
                (51, 1, "heal", 1),
                (61, 1, "heal", 1)
            ),
        )
        db.commit()


def test_discovers_current_class_and_owned_weapon_heals(tmp_path):
    path = tmp_path / "eso.db"
    _write_fixture(path)
    service = ExtremeHealSkillCandidateService(path)
    build = PlayerBuild(EsoClass="Warden")
    progression = CharacterProgression(owned_skill_lines=("Restoration Staff",))

    candidates = service.candidates_for_build(build, progression)

    assert [candidate.name for candidate in candidates] == ["Budding Seeds", "Grand Healing"]
    budding = next(candidate for candidate in candidates if candidate.name == "Budding Seeds")
    assert budding.rank == 4
    assert budding.ability_id == 102
    assert budding.heal_component_count == 2
    assert budding.can_crit is True
    assert budding.legal is True
    assert budding.blockers == ()


def test_blocked_catalog_preserves_class_and_skill_line_reasons(tmp_path):
    path = tmp_path / "eso.db"
    _write_fixture(path)
    service = ExtremeHealSkillCandidateService(path)
    build = PlayerBuild(EsoClass="Warden")
    progression = CharacterProgression(owned_skill_lines=("Restoration Staff",))

    candidates = service.candidates_for_build(build, progression, include_blocked=True)
    by_name = {candidate.name: candidate for candidate in candidates}

    assert by_name["Breath of Life"].legal is False
    assert by_name["Breath of Life"].blockers == (
        "Breath of Life: requires Templar; current build class is Warden",
    )
    assert by_name["Blood Altar"].legal is False
    assert by_name["Blood Altar"].blockers == (
        "Blood Altar: skill line not owned: Undaunted",
    )


def test_passive_and_non_player_heals_never_become_legal_candidates(tmp_path):
    path = tmp_path / "eso.db"
    _write_fixture(path)
    service = ExtremeHealSkillCandidateService(path)
    build = PlayerBuild(EsoClass="Warden")
    progression = CharacterProgression(owned_skill_lines=("Restoration Staff",))

    candidates = service.candidates_for_build(build, progression, include_blocked=True)
    by_name = {candidate.name: candidate for candidate in candidates}

    assert by_name["Passive Heal Thing"].legal is False
    assert "Passive Heal Thing is passive, not an active heal" in by_name["Passive Heal Thing"].blockers
    assert by_name["Creature Heal"].legal is False
    assert "Creature Heal is not marked as a player ability" in by_name["Creature Heal"].blockers


def test_missing_canonical_classification_tables_fail_closed(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE ability (ability_id INTEGER PRIMARY KEY)")

    service = ExtremeHealSkillCandidateService(path)

    try:
        service.candidates_for_build(PlayerBuild(EsoClass="Warden"), CharacterProgression())
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("missing canonical tables must not silently produce an empty catalog")

    assert "skill" in message
    assert "skill_rank" in message
    assert "skill_component_classification" in message
