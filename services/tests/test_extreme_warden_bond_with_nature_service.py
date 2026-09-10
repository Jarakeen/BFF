from __future__ import annotations

from minmax.character_progression import CharacterProgression
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_trigger_relationship import SkillComponentTriggerType
from models.build_model import PlayerBuild
from services.extreme_warden_bond_with_nature_service import (
    ExtremeWardenBondWithNatureService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Bond with Nature" else None

    @staticmethod
    def skill_line_for_ability_name(name):
        return {
            "Blue Betty": "Animal Companions",
            "Combat Prayer": "Restoration Staff",
        }.get(name)


def _service():
    return ExtremeWardenBondWithNatureService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def _ended(source="Blue Betty"):
    return RuntimeEvent(
        time_seconds=5.0,
        trigger=SkillComponentTriggerType.EFFECT_ENDED.value,
        source=source,
    )


def test_bond_with_nature_rank_two_resolves_live_u50_base_self_heal():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Warden"),
        progression=CharacterProgression(passive_ranks={"Bond with Nature": 2}),
        trigger_event=_ended(),
    )

    assert result.resolved
    assert result.base_self_heal == 1530.0
    assert result.passive_rank == 2


def test_bond_with_nature_rank_one_resolves_live_u50_base_self_heal():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Warden"),
        progression=CharacterProgression(passive_ranks={"Bond with Nature": 1}),
        trigger_event=_ended(),
    )

    assert result.resolved
    assert result.base_self_heal == 765.0


def test_bond_with_nature_requires_effect_ended_runtime_event():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Warden"),
        progression=CharacterProgression(passive_ranks={"Bond with Nature": 2}),
        trigger_event=RuntimeEvent(time_seconds=5.0, trigger="cast", source="Blue Betty"),
    )

    assert not result.resolved
    assert "effect_ended" in result.unresolved[0]


def test_bond_with_nature_requires_animal_companions_trigger_source():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Warden"),
        progression=CharacterProgression(passive_ranks={"Bond with Nature": 2}),
        trigger_event=_ended("Combat Prayer"),
    )

    assert not result.resolved
    assert "Animal Companions" in result.unresolved[0]


def test_explicit_subclass_route_can_remove_native_bond_with_nature():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Restoring Light"],
        ),
        progression=CharacterProgression(passive_ranks={"Bond with Nature": 2}),
        trigger_event=_ended(),
    )

    assert not result.resolved
    assert "equipped Animal Companions" in result.unresolved[0]


def test_foreign_class_can_gain_bond_with_nature_through_explicit_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Animal Companions", "Restoring Light", "Dawn's Wrath"],
        ),
        progression=CharacterProgression(passive_ranks={"Bond with Nature": 2}),
        trigger_event=_ended(),
    )

    assert result.resolved
    assert result.base_self_heal == 1530.0


def test_unknown_bond_with_nature_rank_fails_closed():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Warden"),
        progression=CharacterProgression(passive_ranks=None),
        trigger_event=_ended(),
    )

    assert not result.resolved
    assert result.unresolved == ("Bond with Nature passive rank is not recorded",)
