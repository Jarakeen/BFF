from __future__ import annotations

import sqlite3

import services.extreme_hypothetical_class_progression_service as module
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import CharacterProgression
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)


def _write_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_line TEXT,
                is_passive INTEGER
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                rank INTEGER
            );
            """
        )
        db.executemany(
            "INSERT INTO skill(id, name, skill_line, is_passive) VALUES (?, ?, ?, ?)",
            (
                (1, "Flourish", "Animal Companions", 1),
                (2, "Advanced Species", "Animal Companions", 1),
                (3, "Mending", "Restoring Light", 1),
                (4, "Sacred Ground", "Restoring Light", 1),
                (5, "Evocation", "Light Armor", 1),
                (6, "Frozen Armor", "Winter's Embrace", 1),
            ),
        )
        db.executemany(
            "INSERT INTO skill_rank(id, skill_id, rank) VALUES (?, ?, ?)",
            (
                (11, 1, 1), (12, 1, 2),
                (21, 2, 1), (22, 2, 2),
                (31, 3, 1), (32, 3, 2),
                (41, 4, 1), (42, 4, 2),
                (51, 5, 1), (52, 5, 3),
                (61, 6, 1), (62, 6, 2),
            ),
        )
        db.commit()


def _route() -> ExtremeHealClassRoute:
    return ExtremeHealClassRoute(
        base_class=CharacterClass.WARDEN,
        configuration=ClassSkillLineConfiguration(
            equipped_skill_lines=(
                "animal_companions",
                "green_balance",
                "restoring_light",
            )
        ),
    )


def test_normalize_maxes_selected_class_passives_and_preserves_non_class_progression(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = ExtremeHypotheticalClassProgressionService(path)
    progression = CharacterProgression(
        owned_skill_lines=("Light Armor", "Undaunted", "Winter's Embrace"),
        passive_ranks={
            "Evocation": 3,
            "Frozen Armor": 2,
            "Flourish": 1,
        },
        passive_cp_points={"Blessed": 20},
    )

    result = service.normalize(progression, _route())

    assert "Light Armor" in result.owned_skill_lines
    assert "Undaunted" in result.owned_skill_lines
    assert "Winter's Embrace" not in result.owned_skill_lines
    assert {"animal_companions", "green_balance", "restoring_light"}.issubset(
        set(result.owned_skill_lines)
    )
    assert result.passive_rank("Flourish") == 2
    assert result.passive_rank("Advanced Species") == 2
    assert result.passive_rank("Mending") == 2
    assert result.passive_rank("Sacred Ground") == 2
    assert result.passive_rank("Frozen Armor") is None
    assert result.passive_rank("Evocation") == 3
    assert result.passive_cp_allocation("Blessed") == 20


def test_normalize_does_not_invent_passives_from_unequipped_class_lines(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = ExtremeHypotheticalClassProgressionService(path)

    result = service.normalize(CharacterProgression(passive_ranks={}), _route())

    assert result.passive_rank("Flourish") == 2
    assert result.passive_rank("Mending") == 2
    assert result.passive_rank("Frozen Armor") is None
    assert result.passive_rank("Evocation") is None


def test_class_passive_max_rank_evidence_is_reused_across_service_instances(tmp_path, monkeypatch) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    module._class_passive_max_ranks_for_database.cache_clear()

    real_connect = module.sqlite3.connect
    calls = 0

    def counted_connect(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(module.sqlite3, "connect", counted_connect)

    first = ExtremeHypotheticalClassProgressionService(path)
    second = ExtremeHypotheticalClassProgressionService(path)

    first_result = first.normalize(CharacterProgression(), _route())
    second_result = second.normalize(CharacterProgression(), _route())

    assert first_result.passive_rank("Flourish") == 2
    assert second_result.passive_rank("Flourish") == 2
    assert calls == 1


def test_missing_passive_schema_fails_closed(tmp_path) -> None:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE skill (id INTEGER PRIMARY KEY)")

    module._class_passive_max_ranks_for_database.cache_clear()
    service = ExtremeHypotheticalClassProgressionService(path)
    try:
        service.normalize(CharacterProgression(), _route())
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("missing canonical passive schema must fail closed")

    assert "skill" in message
    assert "skill_rank" in message
