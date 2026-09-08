from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.role import Role
from services.rotation_mechanics_dependency_service import (
    RotationMechanicsDependencyService,
)


def _build(**overrides) -> CharacterBuild:
    values = dict(
        name="dependency test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
    )
    values.update(overrides)
    return CharacterBuild(**values)


def _keys(build: CharacterBuild, **kwargs) -> tuple[str, ...]:
    service = RotationMechanicsDependencyService()
    return service.keys(service.discover(character_build=build, **kwargs))


def test_minimal_build_only_requires_structure_and_recovery_when_enabled() -> None:
    assert _keys(_build()) == (
        "saved_build:canonical_structure",
        "heavy_attack:restoration",
    )
    assert _keys(_build(), recovery_enabled=False) == (
        "saved_build:canonical_structure",
    )


def test_set_and_consumable_identity_add_only_relevant_runtime_domains() -> None:
    build = _build(
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                set_id="serpents_disdain",
                weight="light",
            ),
        ),
        potion_id="essence_of_spell_power",
        poison_id="test_poison",
    )

    keys = _keys(build, recovery_enabled=False)

    assert keys == (
        "saved_build:canonical_structure",
        "gear:conditional_topology",
        "armor:weight_passive_semantics",
        "consumables:runtime_resource_and_buff_policy",
    )
    assert "procs:conditional_topology" not in keys
    assert "passives:runtime_semantics" not in keys


def test_runtime_evidence_adds_passive_uptime_assignment_and_encounter_domains() -> None:
    keys = _keys(
        _build(),
        passives=(object(),),
        requirements=(object(),),
        demands=(object(),),
        recovery_enabled=False,
    )

    assert keys == (
        "saved_build:canonical_structure",
        "passives:runtime_semantics",
        "effect_duration:build_modifiers",
        "assignment:rotation_fulfillment_catalog",
        "encounter:target_range_movement_topology",
    )


def test_armor_weight_distribution_has_dedicated_piece_and_type_count_dependency() -> None:
    service = RotationMechanicsDependencyService()
    build = _build(
        armor=(
            ArmorPiece(slot=GearSlot.HEAD, weight="light"),
            ArmorPiece(slot=GearSlot.SHOULDERS, weight="medium"),
            ArmorPiece(slot=GearSlot.CHEST, weight="light"),
            ArmorPiece(slot=GearSlot.HANDS, weight="light"),
            ArmorPiece(slot=GearSlot.WAIST, weight="light"),
            ArmorPiece(slot=GearSlot.LEGS, weight="medium"),
            ArmorPiece(slot=GearSlot.FEET, weight="light"),
        ),
    )

    dependencies = service.discover(
        character_build=build,
        recovery_enabled=False,
    )
    by_key = {item.key: item for item in dependencies}

    assert "gear:conditional_topology" not in by_key
    assert "passives:runtime_semantics" not in by_key
    assert "armor:weight_passive_semantics" in by_key
    assert by_key["armor:weight_passive_semantics"].evidence == (
        "armor_weight_count:light=5",
        "armor_weight_count:medium=2",
        "armor_weight_type_count=2",
    )
    reason = by_key["armor:weight_passive_semantics"].reason.casefold()
    assert "piece counts" in reason
    assert "undaunted mettle" in reason


def test_three_armor_weights_preserve_distinct_composition_for_undaunted_relevance() -> None:
    service = RotationMechanicsDependencyService()
    dependencies = service.discover(
        character_build=_build(
            armor=(
                ArmorPiece(slot=GearSlot.HEAD, weight="light"),
                ArmorPiece(slot=GearSlot.CHEST, weight="medium"),
                ArmorPiece(slot=GearSlot.LEGS, weight="heavy"),
            ),
        ),
        recovery_enabled=False,
    )
    dependency = {
        item.key: item for item in dependencies
    }["armor:weight_passive_semantics"]

    assert dependency.evidence == (
        "armor_weight_count:heavy=1",
        "armor_weight_count:light=1",
        "armor_weight_count:medium=1",
        "armor_weight_type_count=3",
    )


def test_dependency_reasons_are_explanatory_and_keys_are_unique() -> None:
    service = RotationMechanicsDependencyService()
    dependencies = service.discover(
        character_build=_build(
            armor=(ArmorPiece(slot=GearSlot.CHEST, set_id="serpents_disdain"),),
            potion_id="test_potion",
        ),
        requirements=(object(),),
        passives=(object(),),
        recovery_enabled=True,
    )

    keys = service.keys(dependencies)
    assert len(keys) == len(set(keys))
    assert all(item.reason.strip() for item in dependencies)
    assert any("duration" in item.reason.casefold() for item in dependencies)
    assert any("heavy" in item.reason.casefold() for item in dependencies)


def test_dependencies_retain_exact_selected_build_evidence_without_inventing_semantics() -> None:
    service = RotationMechanicsDependencyService()
    dependencies = service.discover(
        character_build=_build(
            armor=(
                ArmorPiece(
                    slot=GearSlot.CHEST,
                    set_id="serpents_disdain",
                    weight="light",
                ),
            ),
            potion_id="essence_of_spell_power",
            poison_id="test_poison",
        ),
        requirements=(object(), object()),
        demands=(object(),),
        recovery_enabled=True,
    )
    by_key = {item.key: item for item in dependencies}

    assert by_key["saved_build:canonical_structure"].evidence == (
        "class=warden",
        "role=healer",
        "build=dependency test",
    )
    assert by_key["gear:conditional_topology"].evidence == (
        "set=serpents_disdain",
        "armor_weight=light",
    )
    assert by_key["armor:weight_passive_semantics"].evidence == (
        "armor_weight_count:light=1",
        "armor_weight_type_count=1",
    )
    assert by_key["consumables:runtime_resource_and_buff_policy"].evidence == (
        "potion=essence_of_spell_power",
        "poison=test_poison",
    )
    assert by_key["effect_duration:build_modifiers"].evidence == (
        "uptime_requirement_count=2",
    )
    assert by_key["encounter:target_range_movement_topology"].evidence == (
        "encounter_demand_count=1",
    )
    assert by_key["heavy_attack:restoration"].evidence == (
        "recovery_heavy_candidate_path=enabled",
    )
