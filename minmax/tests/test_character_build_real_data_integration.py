"""
Integration tests that drive the CharacterBuild -> SupportEffectResolver
pipeline with data traced back to this repository's actual ESO source
data, instead of hand-authored synthetic fixtures.

Data path exercised here:

    real ESO source data
        |
    repository/importer   (CombatEffectImporter, ability_combat_effect
                            explicit mappings, ESO-Hub crawler spot-check
                            data)
        |
    CombatEffectRelationshipRepository /
    validators.KNOWN_PAGE_SPOT_CHECKS
        |
    character_build.combat_effect_relationship_bridge  (generic
                            interaction-record -> EffectRelationship
                            conversion)
        |
    CharacterBuild
        |
    CharacterBuildSupportEffectResolver
        |
    resolved effects

See this module's tail for the full A/B/C breakdown of what is proven
by source data vs. inferred by generic engine logic vs. still missing.
"""

import tempfile
from pathlib import Path

import importers.ability_combat_effect as ability_combat_effect_module
from importers.combat_effect_importer import CombatEffectImporter
from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.combat_effect_relationship_bridge import (
    interaction_record_to_relationship,
    to_effect_identity,
)
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.support_effect_resolver import (
    CharacterBuildSupportEffectResolver,
)
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.combat_effect_relationship_repository import (
    CombatEffectRelationshipRepository,
)
from minmax.role import Role
from validators.validate_eso_hub_skill_data import KNOWN_PAGE_SPOT_CHECKS


def _filler(index: int, skill_line_id: str) -> SlottedSkill:
    return SlottedSkill(skill_id=f"filler_{index}", skill_line_id=skill_line_id)


def _import_real_combat_effects(tmp_path: Path) -> Path:
    """
    Run the real, unmodified CombatEffectImporter against a throwaway
    database. The importer's actual effect/trigger/interaction data is
    hardcoded Python data inside the importer itself (attributed to
    "ESO Wiki combat effects"), not read from `source_file` - the
    dummy file below only satisfies the importer's existence check.
    """
    database_path = tmp_path / "combat_effects.db"
    source_file = tmp_path / "combat_effects.md"
    source_file.write_text("placeholder - not actually parsed", encoding="utf-8")

    CombatEffectImporter(
        database_path=database_path, source_file=source_file
    ).run()

    return database_path


# ============================================================
# A. Facts proven directly by repository source data
# ============================================================


def test_ability_combat_effect_mapping_contains_traced_aggressive_horn_fact():
    """
    Proves the real fact this task traced: the repository's
    ability-effect explicit-mapping data (importers/ability_combat_effect.py)
    now contains an "Aggressive Horn" -> "Major Force" Grants mapping,
    sourced from validators/validate_eso_hub_skill_data.py's
    KNOWN_PAGE_SPOT_CHECKS (a hand-verified inspection of the real
    ESO-Hub page). No target/bar/trigger detail is claimed beyond what
    that source actually states.
    """
    importer = ability_combat_effect_module.AbilityCombatEffectImporter.__new__(
        ability_combat_effect_module.AbilityCombatEffectImporter
    )
    mappings = ability_combat_effect_module.AbilityCombatEffectImporter._explicit_mappings(
        importer
    )

    horn_mappings = [m for m in mappings if m["ability"] == "Aggressive Horn"]

    assert len(horn_mappings) == 1
    assert horn_mappings[0]["effect"] == "Major Force"
    assert horn_mappings[0]["relationship"] == "Grants"


def test_known_page_spot_checks_is_the_traced_source_of_that_fact():
    """
    Proves the mapping above is not an independently-invented claim: it
    traces to the same KNOWN_PAGE_SPOT_CHECKS data used by the ESO-Hub
    skill data validator.
    """
    spot_checks = dict(KNOWN_PAGE_SPOT_CHECKS)

    assert "Aggressive Horn" in spot_checks
    assert spot_checks["Aggressive Horn"]["buffs"] == ["Major Force"]


def test_real_combat_effect_importer_data_for_chilled(tmp_path):
    """
    Proves the real, already-authored ESO Wiki combat-effect data for
    Chilled: it is applied by Frost damage (a trigger), and it applies
    both Minor Maim (unconditionally) and Minor Brittle (conditioned on
    an Ice Staff being the active weapon) - not Major Brittle, and not
    unconditionally, as an earlier synthetic test in this repository
    incorrectly assumed.
    """
    database_path = _import_real_combat_effects(tmp_path)
    repository = CombatEffectRelationshipRepository(database_path)

    triggers = repository.get_triggers("Chilled")
    interactions = repository.get_interactions("Chilled")

    assert any(
        trigger.trigger_type == "Damage" and trigger.damage_type == "Frost"
        for trigger in triggers
    )

    by_target = {record.target_name: record for record in interactions}

    assert "Minor Maim" in by_target
    assert by_target["Minor Maim"].condition is None

    assert "Minor Brittle" in by_target
    assert by_target["Minor Brittle"].condition == "Ice Staff active weapon"
    assert "major_brittle" not in {to_effect_identity(name) for name in by_target}


# ============================================================
# B. Generic engine behavior, driven by the real data above
# ============================================================


def test_status_chain_from_real_combat_effect_data(tmp_path):
    """
    Drives the full path: real importer data -> repository ->
    generic bridge -> CharacterBuild -> resolver -> resolved effects.

    The resolver/relationship engine has no idea what "Chilled" or
    "Minor Brittle" mean - it only sees identities and conditions
    coming from real repository rows. The character-build-authored part
    (a frost-staff skill applying "chilled" when cast) is still
    hand-modeled here, because no repository/service in this codebase
    yet links a specific skill to its status application as a runtime
    object (see the "Not yet available" section below) - only the
    downstream Chilled -> Minor Maim / Minor Brittle interactions are
    driven by real, unmodified importer data.
    """
    database_path = _import_real_combat_effects(tmp_path)
    repository = CombatEffectRelationshipRepository(database_path)
    relationships = tuple(
        interaction_record_to_relationship(record)
        for record in repository.get_interactions("Chilled")
    )

    chilled_identity = to_effect_identity("Chilled")
    assert chilled_identity == "chilled"

    frost_skill = SlottedSkill(
        skill_id="frost_staff_skill",
        skill_line_id="destruction_staff",
        is_cast=True,
        effects=(
            EffectVariant(
                name=chilled_identity,
                layer=EffectLayer.CAST,
                source="Frost Staff Skill",
            ),
        ),
    )
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=tuple(_filler(i, "restoration_staff") for i in range(5))
        + (SlottedSkill(skill_id="ult", skill_line_id="restoration_staff", is_ultimate=True),),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF),
        off_hand=None,
        slots=(frost_skill,) + tuple(_filler(i, "destruction_staff") for i in range(4))
        + (SlottedSkill(skill_id="ult2", skill_line_id="destruction_staff", is_ultimate=True),),
    )
    build = CharacterBuild(
        name="Real Status Chain",
        character_class=CharacterClass.WARDEN,
        role=Role.DD,
        front_bar=front,
        back_bar=back,
    )

    registry = CharacterBuildSupportEffectResolver().resolve(
        build, BarId.BACK, relationships=relationships
    )
    on_front = CharacterBuildSupportEffectResolver().resolve(
        build, BarId.FRONT, relationships=relationships
    )

    by_name = {effect.name: effect for effect in registry.all()}

    # Both real interactions fire once Chilled is present in the
    # resolved set (the engine gates on source-effect presence; it does
    # not itself evaluate "Ice Staff active weapon" as a boolean - see
    # limitation B2 below).
    assert "minor_maim" in by_name
    assert by_name["minor_maim"].magnitude == 5.0
    assert by_name["minor_maim"].duration == 4.0

    assert "minor_brittle" in by_name
    assert by_name["minor_brittle"].magnitude == 10.0
    assert by_name["minor_brittle"].trigger is not None
    assert by_name["minor_brittle"].trigger.condition == "Ice Staff active weapon"

    # Front bar never casts the frost-staff skill, so Chilled (and
    # everything chained from it) correctly does not appear there -
    # this part IS proven by the bar-gating engine logic, not the
    # imported data.
    front_names = {effect.name for effect in on_front.all()}
    assert "chilled" not in front_names
    assert "minor_brittle" not in front_names


def test_aggressive_horn_fact_flows_through_character_build_resolution():
    """
    Uses the real, traced "Aggressive Horn Grants Major Force" fact
    (proven in section A) to author a CharacterBuild ultimate slot, then
    resolves it through the real resolver. The *fact itself* comes from
    repository data; representing it as a slotted ultimate on a specific
    bar is CharacterBuild's job (generic engine behavior), and is not
    itself claimed to be sourced.
    """
    importer = ability_combat_effect_module.AbilityCombatEffectImporter.__new__(
        ability_combat_effect_module.AbilityCombatEffectImporter
    )
    mapping = next(
        m
        for m in ability_combat_effect_module.AbilityCombatEffectImporter._explicit_mappings(
            importer
        )
        if m["ability"] == "Aggressive Horn"
    )

    horn_slot = SlottedSkill(
        skill_id=to_effect_identity(mapping["ability"]),
        skill_line_id="assault",
        is_ultimate=True,
        effects=(
            EffectVariant(
                name=to_effect_identity(mapping["effect"]),
                layer=EffectLayer.ULTIMATE,
                source=mapping["ability"],
            ),
        ),
    )
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=tuple(_filler(i, "dual_wield") for i in range(5)) + (horn_slot,),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=tuple(_filler(i, "dual_wield") for i in range(5)) + (horn_slot,),
    )
    build = CharacterBuild(
        name="Horn Fact Test",
        character_class=CharacterClass.NIGHTBLADE,
        role=Role.DD,
        front_bar=front,
        back_bar=back,
    )

    registry = CharacterBuildSupportEffectResolver().resolve(build, BarId.FRONT)
    force = [e for e in registry.all() if e.name == "major_force"]

    assert len(force) == 1
    assert force[0].source == "Aggressive Horn"


# ============================================================
# C. What remains unavailable from current source data (documented,
#    not guessed) - see also the end-of-task report.
# ============================================================
#
# - Master's Architect (or any gear set's ultimate-triggered proc) has
#   NO source data anywhere in this repository: no raw item dump, no
#   populated gear_set/gear_set_bonus table, no crawler output file.
#   `data/raw/` does not exist in this checkout and data/eso.db is
#   empty. The generic combat_effect_trigger/interaction schema (proven
#   above for Chilled) is fully capable of representing a
#   "cast an Ultimate while a specific set/weapon is equipped ->
#   produces Major Slayer" fact once such a row exists - no code change
#   would be needed, only the data.
# - The `skill` table schema (importers/skills_importer.py) has
#   `skill_type`/`target` INTEGER columns that could distinguish
#   ultimates and target types, but this checkout has no populated rows
#   and no decode table for those integers, so "Aggressive Horn is an
#   ultimate" cannot currently be confirmed from source data - only
#   from general ESO knowledge, which this task instructs not to invent
#   into a resolver fact.
# - No repository/service in minmax/ reads the
#   `ability_combat_effect` table (populated by
#   importers/ability_combat_effect.py) into runtime CombatEffect/
#   EffectVariant objects - this task's tests call its
#   `_explicit_mappings()` data method directly. A generic reader
#   analogous to CombatEffectRelationshipRepository would close this
#   gap for any ability, not just Aggressive Horn.
