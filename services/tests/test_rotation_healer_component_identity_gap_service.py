from types import SimpleNamespace

from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild
from services.rotation_healer_component_identity_gap_service import (
    RotationHealerComponentIdentityGapService,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


class _EmptyBase:
    def get_for_skill_rank(self, skill_rank_id: int):
        return ()


class _Coefficients:
    def __init__(self, *, skill_name: str, skill_rank_id: int, ability_id: int = 1234):
        self.skill_name = skill_name
        self.skill_rank_id = skill_rank_id
        self.ability_id = ability_id

    def resolve_name(self, requested: str):
        assert requested == self.skill_name
        return SimpleNamespace(
            rank=SimpleNamespace(
                name=self.skill_name,
                skill_rank_id=self.skill_rank_id,
                ability_id=self.ability_id,
                coefficients=(SimpleNamespace(coefficient_number=1),),
            ),
            unresolved=(),
        )


class _AuditService(RotationHealerComponentIdentityGapService):
    def __init__(self, *args, description: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.description = description

    def _coef_description(self, ability_id: int) -> str:
        return self.description


def _build(skill_name: str) -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Role="Healer",
        FrontBarSkills=[skill_name],
    )


def test_reviewed_u50_healer_identity_is_not_reported_as_missing_review():
    repo = RotationHealerU50SkillComponentRepository(
        "unused.db",
        base_repository=_EmptyBase(),
    )
    service = _AuditService(
        "unused.db",
        description=(
            "Slam your staff down to activate its blessings, healing you and your allies "
            "in front of you for |cffffff$1|r Health."
        ),
        coefficient_repository=_Coefficients(
            skill_name="Combat Prayer",
            skill_rank_id=repo.COMBAT_PRAYER_RANK_ID,
        ),
        component_repository=repo,
    )

    report = service.inspect(_build("Combat Prayer"))

    assert len(report.rows) == 1
    assert report.rows[0].canonical_effect_kind is SkillEffectKind.HEAL
    assert report.rows[0].text_proves_heal is True
    assert report.review_candidates == ()


def test_text_proven_heal_without_reviewed_identity_remains_a_review_candidate():
    service = _AuditService(
        "unused.db",
        description="You and your allies are healed for |cffffff$1|r Health.",
        coefficient_repository=_Coefficients(
            skill_name="Unreviewed Heal",
            skill_rank_id=999999,
        ),
        component_repository=_EmptyBase(),
    )

    report = service.inspect(_build("Unreviewed Heal"))

    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.canonical_effect_kind is SkillEffectKind.UNKNOWN
    assert row.text_proves_heal is True
    assert row.needs_heal_identity_review is True
    assert report.review_candidates == (row,)


def test_default_gap_audit_uses_same_u50_reviewed_component_view_as_healer_runtime():
    service = RotationHealerComponentIdentityGapService("unused.db")

    assert isinstance(service.components, RotationHealerU50SkillComponentRepository)
