from minmax.skill_component_resource_event import (
    SkillComponentResourceAmountBasis,
    SkillComponentResourceEvent,
    SkillComponentResourceEventType,
    SkillComponentResourceScalingDriver,
    SkillComponentResourceType,
)
from tools import audit_phase6_ambiguous_restore_resource as audit
from tools.audit_phase6_heal_shield_unresolved_taxonomy import UnresolvedHealShieldRow


class _FakeRepository:
    def __init__(self, path):
        self.path = path

    def resolve(self, skill_rank_id, coefficient_number):
        return (
            SkillComponentResourceEvent(
                skill_rank_id=skill_rank_id,
                coefficient_number=coefficient_number,
                event_type=SkillComponentResourceEventType.GAINS_RESOURCE,
                resource_type=SkillComponentResourceType.STAMINA,
                amount_basis=SkillComponentResourceAmountBasis.PERCENT_RESOURCE,
                amount_fraction=0.12,
                max_bonus_fraction=1.0,
                scaling_driver=SkillComponentResourceScalingDriver.CURRENT_HEALTH,
                evidence="restore 12% Stamina; increasing by up to 100% based on current Health",
            ),
        )


def test_ambiguous_restore_promotes_to_stamina_resource(monkeypatch):
    candidates = (
        UnresolvedHealShieldRow(
            skill_rank_id=10,
            coefficient_number=2,
            ability_id=100,
            ability_name="Hircine Example",
            category="ambiguous_restore_shorthand",
            candidate_types=("heal", "shield"),
            resolved_effect_kind=None,
            fragment=(
                "You also restore 12% Stamina, increasing by up to 100% based on how high "
                "your current Health is. Current Restore: $2 While slotted you gain Major Vitality."
            ),
        ),
    )
    monkeypatch.setattr(audit, "load_unresolved_taxonomy", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(audit, "SkillComponentResourceEventRepository", _FakeRepository)

    rows = audit.load_ambiguous_restore_resource_audit("ignored.db")

    assert len(rows) == 1
    assert rows[0].status == "PROMOTED"
    assert rows[0].resource_type == "stamina"
    assert rows[0].amount_basis == "percent_resource"
    assert rows[0].amount_fraction == 0.12
    assert rows[0].max_bonus_fraction == 1.0
    assert rows[0].scaling_driver == "current_health"
