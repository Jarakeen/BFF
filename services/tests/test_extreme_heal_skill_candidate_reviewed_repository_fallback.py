from __future__ import annotations

import sqlite3

from minmax.character_progression import CharacterProgression
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidateService


class _ReviewedComponents:
    def get_for_skill_rank(self, skill_rank_id):
        if int(skill_rank_id) != 6910:
            return ()
        return (
            SkillComponentClassification(
                skill_rank_id=6910,
                coefficient_number=1,
                effect_kind=SkillEffectKind.HEAL,
                can_crit=True,
            ),
        )


def _write_core_skill_schema(path):
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
            INSERT INTO skill(id, name, is_passive)
            VALUES (700, 'Budding Seeds', 0);
            INSERT INTO ability(ability_id, name, class_type, skill_line, is_player, is_passive)
            VALUES (900, 'Budding Seeds', 'Warden', 'Green Balance', 1, 0);
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (6910, 700, 900, 'Budding Seeds', 4, 1);
            """
        )


def test_reviewed_repository_can_discover_heal_without_persisted_classification_table(tmp_path):
    path = tmp_path / 'eso.db'
    _write_core_skill_schema(path)
    service = ExtremeHealSkillCandidateService(
        path,
        component_repository=_ReviewedComponents(),
    )

    candidates = service.candidates_for_build(
        PlayerBuild(EsoClass='Warden'),
        CharacterProgression(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.name == 'Budding Seeds'
    assert candidate.skill_rank_id == 6910
    assert candidate.heal_component_count == 1
    assert candidate.can_crit is True


def test_missing_core_skill_tables_still_fail_closed_without_classification_table(tmp_path):
    path = tmp_path / 'eso.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE ability (ability_id INTEGER PRIMARY KEY)')

    service = ExtremeHealSkillCandidateService(
        path,
        component_repository=_ReviewedComponents(),
    )

    try:
        service.candidates_for_build(PlayerBuild(EsoClass='Warden'), CharacterProgression())
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError('missing core canonical skill tables must fail closed')

    assert 'skill' in message
    assert 'skill_rank' in message
    assert 'skill_component_classification' not in message
