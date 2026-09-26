from __future__ import annotations

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_skill_bar_frontier_service import (
    ExtremeSustainedDPSSkillBarFrontierService,
    ExtremeSustainedDPSSkillBarLegalityContext,
)


def _row(
    ability_id,
    base_id,
    name,
    line,
    *,
    morph=0,
    ultimate=False,
    class_type="",
):
    return {
        "ability_id": ability_id,
        "base_ability_id": base_id,
        "name": name,
        "class_type": class_type,
        "skill_line": line,
        "is_player": 1,
        "is_passive": 0,
        "is_crafted": 0,
        "morph": morph,
        "base_mechanic": 8 if ultimate else 0,
    }


def _rows():
    rows = [
        _row(101, 100, "Base A", "Animal Companions", class_type="Warden"),
        _row(102, 100, "Morph A1", "Animal Companions", morph=1, class_type="Warden"),
        _row(103, 100, "Morph A2", "Animal Companions", morph=2, class_type="Warden"),
        _row(201, 200, "Class B", "Animal Companions", class_type="Warden"),
        _row(301, 300, "Guild C", "Fighters Guild"),
        _row(401, 400, "Weapon D", "Destruction Staff"),
        _row(501, 500, "Unowned Guild", "Mages Guild"),
        _row(601, 600, "Ultimate A", "Animal Companions", ultimate=True, class_type="Warden"),
        _row(602, 600, "Ultimate Morph", "Animal Companions", morph=1, ultimate=True, class_type="Warden"),
    ]
    return tuple(rows)


def _context():
    return ExtremeSustainedDPSSkillBarLegalityContext(
        character_class="Warden",
        class_skill_lines=("Animal Companions", "Green Balance", "Winter's Embrace"),
        owned_skill_lines=("Fighters Guild",),
        weapon_skill_lines=("Destruction Staff",),
    )


def test_skill_bar_frontier_preserves_morphs_and_requires_shared_line_ownership() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    families = service._families(_rows(), _context(), ultimate=False)

    assert tuple(row.base_ability_id for row in families) == (100, 200, 400, 300)
    family_a = next(row for row in families if row.base_ability_id == 100)
    assert tuple(item.name for item in family_a.alternatives) == (
        "Base A",
        "Morph A1",
        "Morph A2",
    )
    assert all(row.base_ability_id != 500 for row in families)


def test_bar_denominator_keeps_empty_slots_and_collapses_normal_slot_permutations() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    indexer = service._indexer(_context())

    # Four normal families, with alternative counts 3,1,1,1:
    # k=0 => 1
    # k=1 => 6
    # k=2 => 12
    # k=3 => 10
    # k=4 => 3
    # normal total = 32. Ultimate = empty + 2 alternatives = 3.
    assert indexer.normal_candidate_count == 32
    assert indexer.ultimate_candidate_count == 3
    assert indexer.candidate_count == 96


def test_one_family_never_appears_twice_on_same_bar() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    indexer = service._indexer(_context())

    for index in range(indexer.candidate_count):
        state = indexer.state_at(index)
        ids = tuple(row.base_ability_id for row in state.normal_skills)
        assert len(ids) == len(set(ids))


def test_two_bar_frontier_is_lazy_cartesian_product_and_materializes_names() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    context = _context()
    frontier = service.frontier(front_context=context, back_context=context)

    assert frontier.denominator_proven is True
    assert frontier.front_candidate_count == 96
    assert frontier.back_candidate_count == 96
    assert frontier.candidate_count == 96 * 96

    candidate = service.candidate_at(
        PlayerBuild(EsoClass="Warden"),
        front_context=context,
        back_context=context,
        index=frontier.candidate_count - 1,
    )
    assert len(candidate.build.FrontBarSkills) == 6
    assert len(candidate.build.BackBarSkills) == 6


def test_one_bar_only_collapses_back_denominator_to_empty_bar() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    context = _context()
    frontier = service.frontier(
        front_context=context,
        back_context=context,
        one_bar_only=True,
    )

    assert frontier.back_candidate_count == 1
    candidate = service.candidate_at(
        PlayerBuild(EsoClass="Warden"),
        front_context=context,
        back_context=context,
        index=0,
        one_bar_only=True,
    )
    assert candidate.build.BackBarSkills == ["", "", "", "", "", ""]


def test_invalid_two_bar_index_fails_closed() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    context = _context()
    frontier = service.frontier(front_context=context, back_context=context)

    with pytest.raises(IndexError):
        service.candidate_at(
            PlayerBuild(),
            front_context=context,
            back_context=context,
            index=frontier.candidate_count,
        )


def test_explicit_subclass_line_is_legal_even_when_owned_by_foreign_base_class() -> None:
    rows = (
        *_rows(),
        _row(
            701,
            700,
            "Foreign Class Skill",
            "Ardent Flame",
            class_type="Dragonknight",
        ),
    )
    context = ExtremeSustainedDPSSkillBarLegalityContext(
        character_class="Warden",
        class_skill_lines=("Animal Companions", "Green Balance", "Ardent Flame"),
        owned_skill_lines=("Fighters Guild",),
        weapon_skill_lines=("Destruction Staff",),
    )
    families = ExtremeSustainedDPSSkillBarFrontierService(
        skill_rows=rows
    )._families(rows, context, ultimate=False)

    assert any(row.base_ability_id == 700 for row in families)


def test_skill_bar_frontier_rejects_boolean_candidate_index() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    context = _context()

    with pytest.raises(TypeError, match="candidate index must be an integer"):
        service.candidate_at(
            PlayerBuild(),
            front_context=context,
            back_context=context,
            index=True,
        )


def test_skill_bar_frontier_requires_strict_one_bar_only_flag() -> None:
    service = ExtremeSustainedDPSSkillBarFrontierService(skill_rows=_rows())
    context = _context()

    with pytest.raises(TypeError, match="one_bar_only must be boolean"):
        service.frontier(
            front_context=context,
            back_context=context,
            one_bar_only=1,
        )


def test_skill_bar_context_requires_strict_world_state_flags_and_tuples() -> None:
    with pytest.raises(TypeError, match="vampire flag must be boolean"):
        ExtremeSustainedDPSSkillBarLegalityContext(
            character_class="Warden",
            vampire="false",
        )

    with pytest.raises(TypeError, match="owned_skill_lines must be a tuple"):
        ExtremeSustainedDPSSkillBarLegalityContext(
            character_class="Warden",
            owned_skill_lines=["Fighters Guild"],
        )
