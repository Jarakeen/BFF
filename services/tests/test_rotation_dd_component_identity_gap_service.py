from types import SimpleNamespace

from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_dd_component_identity_gap_service import (
    RotationDDComponentIdentityGapService,
)


class _Coefficients:
    def __init__(self, rows):
        self.rows = dict(rows)

    def resolve_name(self, name):
        return self.rows[name]


class _Components:
    def __init__(self, rows):
        self.rows = dict(rows)

    def get_for_skill_rank(self, skill_rank_id):
        return self.rows.get(skill_rank_id, ())


class _Service(RotationDDComponentIdentityGapService):
    def __init__(self, *, coefficients, components, descriptions):
        super().__init__(
            "unused.db",
            coefficient_repository=coefficients,
            component_repository=components,
        )
        self.descriptions = dict(descriptions)

    def _coef_description(self, ability_id: int) -> str:
        return self.descriptions.get(ability_id, "")


def _rank(name: str, rank_id: int, ability_id: int, coefficient_numbers=(1,)):
    return SimpleNamespace(
        rank=SimpleNamespace(
            name=name,
            skill_rank_id=rank_id,
            ability_id=ability_id,
            coefficients=tuple(
                SimpleNamespace(coefficient_number=number)
                for number in coefficient_numbers
            ),
        ),
        unresolved=(),
    )


def test_text_damage_without_canonical_row_becomes_review_candidate() -> None:
    build = PlayerBuild(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role="DD",
        FrontBarSkills=["Unnerving Boneyard", "", "", "", "", ""],
    )
    service = _Service(
        coefficients=_Coefficients(
            {"Unnerving Boneyard": _rank("Unnerving Boneyard", 7308, 12345)}
        ),
        components=_Components({}),
        descriptions={
            12345: "Desecrate the ground, dealing $1 Frost Damage every 1 second for 10 seconds."
        },
    )

    report = service.inspect(build)

    assert report.unresolved == ()
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.skill_rank_id == 7308
    assert row.coefficient_number == 1
    assert row.text_proves_damage is True
    assert row.text_proves_periodic_damage is True
    assert row.canonical_proves_damage is False
    assert row.needs_damage_identity_review is True
    assert row.needs_periodic_identity_review is True
    assert report.review_candidates == (row,)


def test_existing_canonical_periodic_damage_is_not_a_review_candidate() -> None:
    build = PlayerBuild(
        FrontBarSkills=["Stampede", "", "", "", "", ""],
    )
    canonical = SkillComponentClassification(
        skill_rank_id=5134,
        coefficient_number=1,
        effect_kind=SkillEffectKind.DAMAGE,
        damage_type="physical",
        is_dot=True,
        is_aoe=True,
        can_crit=True,
        source="reviewed",
    )
    service = _Service(
        coefficients=_Coefficients({"Stampede": _rank("Stampede", 5134, 23456)}),
        components=_Components({5134: (canonical,)}),
        descriptions={
            23456: "After charging, the area deals $1 Physical Damage every 1 second for 10 seconds."
        },
    )

    report = service.inspect(build)

    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.canonical_proves_periodic_damage is True
    assert row.needs_damage_identity_review is False
    assert row.needs_periodic_identity_review is False
    assert report.review_candidates == ()


def test_non_damage_coefficients_are_not_promoted_from_nearby_skill_text() -> None:
    build = PlayerBuild(
        FrontBarSkills=["Utility Skill", "", "", "", "", ""],
    )
    service = _Service(
        coefficients=_Coefficients({"Utility Skill": _rank("Utility Skill", 99, 34567)}),
        components=_Components({}),
        descriptions={34567: "Increase the duration of the effect to $1 seconds."},
    )

    report = service.inspect(build)

    assert report.rows == ()
    assert report.review_candidates == ()


def test_unresolved_skill_identity_is_preserved() -> None:
    build = PlayerBuild(
        FrontBarSkills=["Heroic Banner", "", "", "", "", ""],
    )
    service = _Service(
        coefficients=_Coefficients(
            {
                "Heroic Banner": SimpleNamespace(
                    rank=None,
                    unresolved=("Ability Entity Id not found: heroic_banner",),
                )
            }
        ),
        components=_Components({}),
        descriptions={},
    )

    report = service.inspect(build)

    assert report.rows == ()
    assert report.unresolved == (
        "front slot 1 Heroic Banner: Ability Entity Id not found: heroic_banner",
    )
