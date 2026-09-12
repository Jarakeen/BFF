from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from services.rotation_dd_reviewed_skill_component_repository import (
    RotationDDReviewedSkillComponentRepository,
)


class _BaseRepository:
    def __init__(self):
        self.calls = []

    def get_for_skill_rank(self, skill_rank_id):
        self.calls.append(int(skill_rank_id))
        if int(skill_rank_id) == 9999:
            return (
                SkillComponentClassification(
                    skill_rank_id=9999,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.UTILITY,
                    source="base-only",
                ),
            )
        return ()


def test_reviewed_rows_are_complete_damage_identities() -> None:
    repository = RotationDDReviewedSkillComponentRepository(
        "unused.db",
        base_repository=_BaseRepository(),
    )

    boneyard = repository.get_component(7308, 1)
    stampede = repository.get_component(5134, 2)
    venom_skull = repository.get_component(7188, 1)

    assert boneyard is not None
    assert boneyard.is_complete_damage_identity
    assert boneyard.effect_kind is SkillEffectKind.DAMAGE
    assert boneyard.damage_type == "frost"
    assert boneyard.is_dot is True
    assert boneyard.is_aoe is True
    assert boneyard.can_crit is True

    assert stampede is not None
    assert stampede.is_complete_damage_identity
    assert stampede.is_dot is True
    assert stampede.damage_type == "physical"

    assert venom_skull is not None
    assert venom_skull.is_complete_damage_identity
    assert venom_skull.is_dot is False
    assert venom_skull.is_aoe is False


def test_reviewed_rank_contains_only_exact_reviewed_coefficients() -> None:
    repository = RotationDDReviewedSkillComponentRepository(
        "unused.db",
        base_repository=_BaseRepository(),
    )

    rows = repository.get_for_skill_rank(6053)

    assert tuple(row.coefficient_number for row in rows) == (1, 2)
    assert rows[0].is_dot is False
    assert rows[1].is_dot is True


def test_unreviewed_rank_delegates_to_base_repository_unchanged() -> None:
    base = _BaseRepository()
    repository = RotationDDReviewedSkillComponentRepository(
        "unused.db",
        base_repository=base,
    )

    rows = repository.get_for_skill_rank(9999)

    assert base.calls == [9999]
    assert len(rows) == 1
    assert rows[0].source == "base-only"
    assert rows[0].effect_kind is SkillEffectKind.UTILITY


def test_unreviewed_coefficient_is_not_fabricated() -> None:
    repository = RotationDDReviewedSkillComponentRepository(
        "unused.db",
        base_repository=_BaseRepository(),
    )

    assert repository.get_component(7188, 2) is None
