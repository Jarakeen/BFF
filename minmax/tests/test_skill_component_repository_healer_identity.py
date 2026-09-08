from __future__ import annotations

import sqlite3

from minmax.skill_component_classification import HealRecipientScope, HealTemporalScope, SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository


def _create_base_table(db: sqlite3.Connection, *, healer_columns: bool) -> None:
    extra = """
        , heal_recipient_scope TEXT
        , heal_temporal_scope TEXT
        , heal_recipient_key TEXT
        , heal_event_key TEXT
    """ if healer_columns else ""
    db.execute(
        f"""
        CREATE TABLE skill_component_classification (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            effect_kind TEXT,
            damage_type TEXT,
            is_dot INTEGER,
            is_aoe INTEGER,
            can_crit INTEGER,
            source TEXT,
            confidence REAL
            {extra}
        )
        """
    )


def test_repository_hydrates_reviewed_healer_event_identity(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        _create_base_table(db, healer_columns=True)
        db.execute(
            """
            INSERT INTO skill_component_classification (
                skill_rank_id, coefficient_number, effect_kind, is_dot, is_aoe,
                can_crit, source, confidence, heal_recipient_scope,
                heal_temporal_scope, heal_recipient_key, heal_event_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (123, 2, "heal", 1, 1, 1, "reviewed", 1.0, "group", "periodic", "allies", "hot_tick"),
        )

    component = SkillComponentRepository(path).get_component(123, 2)

    assert component is not None
    assert component.effect_kind is SkillEffectKind.HEAL
    assert component.heal_recipient_scope is HealRecipientScope.GROUP
    assert component.heal_temporal_scope is HealTemporalScope.PERIODIC
    assert component.heal_recipient_key == "allies"
    assert component.heal_event_key == "hot_tick"


def test_repository_remains_compatible_with_legacy_schema(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        _create_base_table(db, healer_columns=False)
        db.execute(
            """
            INSERT INTO skill_component_classification (
                skill_rank_id, coefficient_number, effect_kind, is_dot, is_aoe,
                can_crit, source, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (123, 1, "heal", 0, 0, 1, "legacy", 0.9),
        )

    component = SkillComponentRepository(path).get_component(123, 1)

    assert component is not None
    assert component.effect_kind is SkillEffectKind.HEAL
    assert component.heal_recipient_scope is None
    assert component.heal_temporal_scope is None
    assert component.heal_recipient_key is None
    assert component.heal_event_key is None


def test_invalid_optional_healer_enum_values_fail_closed(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        _create_base_table(db, healer_columns=True)
        db.execute(
            """
            INSERT INTO skill_component_classification (
                skill_rank_id, coefficient_number, effect_kind, source,
                heal_recipient_scope, heal_temporal_scope
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (123, 3, "heal", "bad reviewed row", "everyoneish", "sometimes"),
        )

    component = SkillComponentRepository(path).get_component(123, 3)

    assert component is not None
    assert component.heal_recipient_scope is None
    assert component.heal_temporal_scope is None
