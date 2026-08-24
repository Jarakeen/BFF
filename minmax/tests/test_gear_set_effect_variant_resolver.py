"""
Focused tests for the generic GearSet -> EffectVariant bridge
(minmax/gear_set_effect_variant_resolver.py + minmax/gear_set_known_effects.py).

Master Architect (gear_set id 332, 5-piece bonus id 1493) is the
acceptance test named in the task, but nothing under test here is
Master-Architect-specific code - it is the resolver being driven by one
row of known-effect data. A second, unmapped bonus and a second,
unrelated set are included specifically to prove the resolver never
guesses at bonuses it doesn't recognize.

Uses a small on-disk sqlite fixture built with the exact same schema as
importers/gear_set_importer.py (gear_set / gear_set_bonus), so these
tests do not depend on data/eso.db being present.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_availability import resolve_available_effects
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from minmax.character_build.support_effect_resolver import (
    CharacterBuildSupportEffectResolver,
)
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_known_effects import (
    MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID,
    MASTER_ARCHITECT_SET_ID,
)
from minmax.gear_set_repository import GearSetRepository
from minmax.role import Role
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType

OTHER_SET_ID = 999
OTHER_SET_UNMAPPED_BONUS_ID = 9001


def _build_fixture_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE gear_set (
                id                  INTEGER PRIMARY KEY,
                name                TEXT NOT NULL,
                category            TEXT,
                max_equip_count     INTEGER
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE gear_set_bonus (
                id                  INTEGER PRIMARY KEY,
                set_id              INTEGER NOT NULL,
                piece_count         INTEGER NOT NULL,
                description         TEXT,
                UNIQUE(set_id, piece_count),
                FOREIGN KEY(set_id) REFERENCES gear_set(id)
            )
            """
        )

        connection.execute(
            "INSERT INTO gear_set (id, name, category, max_equip_count) "
            "VALUES (?, ?, ?, ?)",
            (MASTER_ARCHITECT_SET_ID, "Master Architect", "trial", 5),
        )

        # Real Master Architect tooltip text (UESP/eso-hub), included
        # verbatim to prove this resolver does NOT need to parse it -
        # the mapping comes from gear_set_known_effects.py, not from
        # this description string.
        bonuses = [
            (1490, MASTER_ARCHITECT_SET_ID, 2, "(2 items) Adds 25-1096 Maximum Magicka"),
            (
                1491,
                MASTER_ARCHITECT_SET_ID,
                3,
                "(3 items) Gain Minor Slayer at all times, increasing your "
                "damage done to Dungeon, Trial, and Arena Monsters by 5%.",
            ),
            (1492, MASTER_ARCHITECT_SET_ID, 4, "(4 items) Adds 3-129 Weapon and Spell Damage"),
            (
                MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID,
                MASTER_ARCHITECT_SET_ID,
                5,
                "(5 items) When you use an Ultimate ability while in combat, "
                "you and the closest 5 group members within |cffffff28|r meters "
                "of you gain Major Slayer for 1 second per 10 Ultimate spent, "
                "increasing your damage done to Dungeon, Trial, and Arena "
                "Monsters by |cffffff10|r%.",
            ),
        ]
        connection.executemany(
            "INSERT INTO gear_set_bonus (id, set_id, piece_count, description) "
            "VALUES (?, ?, ?, ?)",
            bonuses,
        )

        # An unrelated set with a bonus that has NO known-effect mapping,
        # to prove the resolver does not guess.
        connection.execute(
            "INSERT INTO gear_set (id, name, category, max_equip_count) "
            "VALUES (?, ?, ?, ?)",
            (OTHER_SET_ID, "Some Other Set", "dungeon", 5),
        )
        connection.execute(
            "INSERT INTO gear_set_bonus (id, set_id, piece_count, description) "
            "VALUES (?, ?, ?, ?)",
            (
                OTHER_SET_UNMAPPED_BONUS_ID,
                OTHER_SET_ID,
                5,
                "(5 items) When you deal damage, you have a chance to summon "
                "a friendly clannfear for 10 seconds.",
            ),
        )

        connection.commit()
    finally:
        connection.close()


@pytest.fixture()
def repository(tmp_path: Path) -> GearSetRepository:
    db_path = tmp_path / "gear_sets_fixture.db"
    _build_fixture_db(db_path)
    return GearSetRepository(db_path)


@pytest.fixture()
def resolver(repository: GearSetRepository) -> GearSetEffectVariantResolver:
    return GearSetEffectVariantResolver(repository)


# ============================================================
# 5-piece Master Architect resolves
# ============================================================

def test_five_piece_master_architect_resolves(resolver: GearSetEffectVariantResolver) -> None:
    variants = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)

    assert len(variants) == 1


def test_fewer_than_five_pieces_does_not_grant_the_bonus(
    resolver: GearSetEffectVariantResolver,
) -> None:
    variants = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=4)

    assert variants == []


def test_zero_pieces_resolves_nothing(resolver: GearSetEffectVariantResolver) -> None:
    assert resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=0) == []


# ============================================================
# Resolves to canonical major_slayer - never a new identity
# ============================================================

def test_resolves_to_canonical_major_slayer(resolver: GearSetEffectVariantResolver) -> None:
    variants = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)

    assert variants[0].name == "major_slayer"


# ============================================================
# Structural fields preserved
# ============================================================

def test_structural_fields_are_preserved(resolver: GearSetEffectVariantResolver) -> None:
    variant = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)[0]

    assert variant.magnitude == 10.0
    assert variant.target_type == SupportTargetType.GROUP
    assert variant.target_count == 5
    assert variant.range == 28.0
    assert variant.trigger == "ultimate_activation_in_combat"
    assert variant.duration == 1.0
    assert variant.scaling == "1 second per 10 Ultimate spent"

    # Not explicitly required by the task, but must not silently regress:
    assert variant.layer == EffectLayer.PROC
    assert variant.category == SupportEffectCategory.BUFF
    assert variant.stacking == StackingBehavior.UNIQUE
    assert variant.exclusivity_group == "major_slayer"


def test_ultimate_scaling_is_preserved_structurally_not_evaluated(
    resolver: GearSetEffectVariantResolver,
) -> None:
    """
    The task explicitly forbids evaluating the Ultimate-spent scaling
    formula. `scaling` must remain the descriptive string, and `duration`
    must remain the BASE duration (1 second), never a computed value.
    """
    variant = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)[0]

    assert isinstance(variant.scaling, str)
    assert variant.duration == 1.0  # base duration, not a resolved value


# ============================================================
# No duplicate Major Slayer effect is created
# ============================================================

def test_no_duplicate_major_slayer_effect_is_created(
    resolver: GearSetEffectVariantResolver,
) -> None:
    variants = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)

    major_slayer_variants = [v for v in variants if v.name == "major_slayer"]

    assert len(major_slayer_variants) == 1


def test_resolving_twice_does_not_accumulate_duplicates(
    resolver: GearSetEffectVariantResolver,
) -> None:
    first = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)
    second = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)

    assert len(first) == 1
    assert len(second) == 1
    assert first[0] == second[0]  # same value, but two independent instances
    assert first[0] is not second[0]


# ============================================================
# No guessing at unmapped bonuses
# ============================================================

def test_unmapped_bonus_contributes_nothing(resolver: GearSetEffectVariantResolver) -> None:
    variants = resolver.resolve(OTHER_SET_ID, equipped_piece_count=5)

    assert variants == []


def test_lower_tier_bonuses_without_mappings_are_skipped_not_guessed(
    resolver: GearSetEffectVariantResolver,
) -> None:
    """
    Master Architect's 2/3/4-piece bonuses have no known-effect entries
    in this test's registry snapshot and must not silently produce
    something for them either - only the registered 5-piece bonus
    resolves.
    """
    variants = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)

    assert {variant.source for variant in variants} == {"Master Architect (5)"}


# ============================================================
# Integration: flows through the EXISTING, unmodified
# CharacterBuild -> EffectVariant -> SupportEffect pipeline
# ============================================================

def test_resolved_variant_flows_through_existing_character_build_pipeline(
    resolver: GearSetEffectVariantResolver,
) -> None:
    """
    Proves the bridge actually plugs into the existing architecture:
    attach the resolver's output onto an ArmorPiece exactly as
    support_effect_resolver.py's own docstring already describes, and
    confirm effect_availability.py + CharacterBuildSupportEffectResolver
    (both unmodified) carry it all the way through to a SupportEffect
    with every field intact.
    """
    variant = resolver.resolve(MASTER_ARCHITECT_SET_ID, equipped_piece_count=5)[0]

    piece = ArmorPiece(
        slot=GearSlot.CHEST,
        category=GearPieceCategory.SET_PIECE,
        set_id=str(MASTER_ARCHITECT_SET_ID),
        effects=(variant,),
    )

    build = CharacterBuild(
        name="Master Architect bridge test",
        character_class=CharacterClass.SORCERER,
        role=Role.DD,
        armor=(piece,),
    )

    resolved = resolve_available_effects(build, BarId.FRONT)

    major_slayer = [effect for effect in resolved if effect.name == "major_slayer"]
    assert len(major_slayer) == 1

    registry = CharacterBuildSupportEffectResolver().resolve(build, BarId.FRONT)
    support_effects = [effect for effect in registry.all() if effect.name == "major_slayer"]

    assert len(support_effects) == 1

    support_effect = support_effects[0]
    assert support_effect.magnitude == 10.0
    assert support_effect.target_type == SupportTargetType.GROUP
    assert support_effect.target_count == 5
    assert support_effect.duration == 1.0
    assert support_effect.exclusivity_group == "major_slayer"
    assert support_effect.trigger is not None
    assert support_effect.trigger.trigger == "ultimate_activation_in_combat"
