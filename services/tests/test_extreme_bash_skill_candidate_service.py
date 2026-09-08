from services.extreme_bash_skill_candidate_service import ExtremeBashSkillCandidateService
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


class FakeCandidateService:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def candidates(self, context, *, ultimate=None):
        assert context.equipped_weapon_lines == ("One Hand and Shield",)
        assert ultimate is False
        return self.rows


def row(name: str, description: str, ability_id: int = 100) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=ability_id,
        name=name,
        class_type="",
        skill_line="One Hand and Shield",
        skill_type="Active",
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=ability_id,
        max_rank=4,
        max_rank_ability_id=ability_id,
        description=description,
        domain=ExtremeSkillDomain.WEAPON,
    )


def context() -> ExtremePlayerSkillLegalityContext:
    return ExtremePlayerSkillLegalityContext(
        equipped_class_lines=(),
        equipped_weapon_lines=("One Hand and Shield",),
    )


def test_filters_to_explicit_bash_classified_active_abilities():
    service = ExtremeBashSkillCandidateService(
        FakeCandidateService(
            (
                row(
                    "Power Bash",
                    "Strike an enemy with your shield. This ability's damage is considered Bash damage and interrupts the enemy if they are casting.",
                    1,
                ),
                row("Puncture", "Thrust your weapon with disciplined precision.", 2),
            )
        )
    )

    result = service.candidates(context())

    assert [candidate.name for candidate in result] == ["Power Bash"]
    assert result[0].bash_classified is True
    assert result[0].standard_bash_formula_channel is False
    assert result[0].mechanic_complete is True


def test_power_slam_preserves_conditional_resentment_cost_reduction():
    service = ExtremeBashSkillCandidateService(
        FakeCandidateService(
            (
                row(
                    "Power Slam",
                    "Strike an enemy full-force with your shield, dealing Physical Damage. While slotted, blocking any attack grants you Resentment, which reduces the cost of your next Power Slam cast within 10 seconds by 50%. This ability's damage is considered Bash damage and interrupts the enemy if they are casting.",
                    3,
                ),
            )
        )
    )

    result = service.candidates(context())[0]

    assert result.name == "Power Slam"
    assert result.conditional_cost_reduction == -0.5
    assert result.conditional_cost_window_seconds == 10.0
    assert result.standard_bash_formula_channel is False


def test_reverberating_bash_is_classified_without_inventing_standard_bash_bonus():
    service = ExtremeBashSkillCandidateService(
        FakeCandidateService(
            (
                row(
                    "Reverberating Bash",
                    "Strike an enemy full-force with your shield, dealing Physical Damage and stunning them. This ability's damage is considered Bash damage and interrupts the enemy if they are casting.",
                    4,
                ),
            )
        )
    )

    result = service.candidates(context())[0]

    assert result.name == "Reverberating Bash"
    assert result.standard_bash_formula_channel is False
    assert result.conditional_cost_reduction is None


def test_unrelated_word_bash_does_not_create_false_classification():
    service = ExtremeBashSkillCandidateService(
        FakeCandidateService(
            (
                row(
                    "Fake Skill",
                    "Bash the enemy with a dramatic flourish, because tooltip prose is a terrible API.",
                    5,
                ),
            )
        )
    )

    assert service.candidates(context()) == ()
