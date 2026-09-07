from __future__ import annotations

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from services.extreme_class_configuration_service import ExtremeClassConfigurationService


def test_each_base_class_enumerates_pure_and_subclass_candidates():
    for base_class in CharacterClass:
        candidates = ExtremeClassConfigurationService.candidates_for_base_class(base_class)

        assert len(candidates) == 460
        pure = [candidate for candidate in candidates if candidate.is_pure_class]
        subclassed = [candidate for candidate in candidates if not candidate.is_pure_class]
        assert len(pure) == 1
        assert len(subclassed) == 459
        assert pure[0].class_mastery_available is True
        assert all(candidate.class_mastery_available is False for candidate in subclassed)


def test_every_enumerated_configuration_passes_canonical_legality_validation():
    for candidate in ExtremeClassConfigurationService.all_candidates():
        config = ClassSkillLineConfiguration(
            equipped_skill_lines=candidate.equipped_skill_lines,
        )
        assert config.validate(candidate.base_class) == ()


def test_subclass_candidates_retain_native_line_and_borrow_from_distinct_classes():
    for candidate in ExtremeClassConfigurationService.candidates_for_base_class(CharacterClass.NIGHTBLADE):
        if candidate.is_pure_class:
            continue

        native = CLASS_SKILL_LINES[candidate.base_class]
        assert set(candidate.equipped_skill_lines) & native
        assert 1 <= len(candidate.foreign_skill_lines) <= 2

        owners = []
        for line in candidate.foreign_skill_lines:
            owner = next(
                character_class
                for character_class, lines in CLASS_SKILL_LINES.items()
                if line in lines
            )
            owners.append(owner)
        assert len(owners) == len(set(owners))


def test_all_candidate_count_is_complete_and_deduplicated():
    candidates = ExtremeClassConfigurationService.all_candidates()

    assert len(candidates) == 7 * 460
    keys = {
        (candidate.base_class, candidate.equipped_skill_lines)
        for candidate in candidates
    }
    assert len(keys) == len(candidates)


def test_objective_checklist_includes_class_mastery_and_legal_gear_boundaries():
    checklist = ExtremeClassConfigurationService.objective_checklist()

    assert "pure class versus subclass configuration" in checklist
    assert "Class Mastery passives for pure-class candidates" in checklist
    assert "maximum one Mythic" in checklist
    assert "arena weapons" in checklist
    assert "legal gear-slot package by piece-count contribution" in checklist
