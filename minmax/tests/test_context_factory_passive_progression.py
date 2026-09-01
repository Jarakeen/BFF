from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory


class _SkillRepository:
    MAX_RANKS = {
        "Flourish": 2,
        "Advanced Species": 2,
        "Frozen Armor": 2,
        "Evocation": 3,
    }

    def passive_max_rank(self, name):
        return self.MAX_RANKS.get(name)

    def skill_line_for_ability_name(self, name, *, class_name=""):
        return "Animal Companions" if name == "Bird of Prey" else None


def test_maxed_passive_gate_distinguishes_unknown_zero_partial_and_maxed():
    factory = BuildCalculationContextFactory(skill_line_repository=_SkillRepository())

    unknown = CharacterProgression(passive_ranks={})
    assert factory._maxed_passive(unknown, "Flourish") == (
        False,
        "Passive rank is not recorded for character: Flourish",
    )

    zero = CharacterProgression(passive_ranks={"Flourish": 0})
    assert factory._maxed_passive(zero, "Flourish") == (False, None)

    partial = CharacterProgression(passive_ranks={"Flourish": 1})
    assert factory._maxed_passive(partial, "Flourish") == (
        False,
        "Partial passive rank is not yet modeled: Flourish 1/2",
    )

    maxed = CharacterProgression(passive_ranks={"Flourish": 2})
    assert factory._maxed_passive(maxed, "Flourish") == (True, None)


def test_irrelevant_skill_line_does_not_create_missing_passive_noise():
    factory = BuildCalculationContextFactory(skill_line_repository=_SkillRepository())
    progression = CharacterProgression(passive_ranks={})

    assert factory._maxed_passive(progression, "Evocation", relevant=False) == (False, None)


def test_legacy_progression_preserves_compatibility_gate():
    factory = BuildCalculationContextFactory(skill_line_repository=_SkillRepository())
    progression = CharacterProgression(passive_ranks=None)

    assert factory._maxed_passive(progression, "Flourish") == (None, None)
