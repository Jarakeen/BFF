from __future__ import annotations

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.extreme_sorcerer_skill_component_repository import (
    ExtremeSorcererSkillComponentRepository,
)


class _BaseRepository:
    def __init__(self, rows=()):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, _skill_rank_id):
        return self.rows


def _repository(rows=()):
    return ExtremeSorcererSkillComponentRepository(
        "ignored.db",
        base_repository=_BaseRepository(rows),
    )


def test_winged_twilight_separates_friendly_target_and_pet_self_heals():
    rows = _repository().get_for_skill_rank(4845)
    by_number = {row.coefficient_number: row for row in rows}

    assert by_number[3].effect_kind is SkillEffectKind.HEAL
    assert by_number[3].heal_recipient_scope is HealRecipientScope.ALLY
    assert by_number[3].heal_recipient_key == "friendly_target"
    assert by_number[4].heal_recipient_scope is HealRecipientScope.PET
    assert by_number[4].heal_recipient_key == "summoned_pet"
    assert by_number[3].heal_event_key == by_number[4].heal_event_key == "pet_special_activation"
    assert by_number[3].can_crit is True
    assert by_number[4].can_crit is True


def test_twilight_matriarch_marks_two_friendly_targets_as_group_event():
    rows = _repository().get_for_skill_rank(4847)
    by_number = {row.coefficient_number: row for row in rows}

    assert by_number[3].is_aoe is True
    assert by_number[3].heal_recipient_scope is HealRecipientScope.GROUP
    assert by_number[3].heal_temporal_scope is HealTemporalScope.DIRECT
    assert by_number[3].heal_recipient_key == "friendly_targets"
    assert by_number[3].can_crit is True
    assert by_number[4].heal_recipient_scope is HealRecipientScope.PET
    assert by_number[4].can_crit is True


def test_unstable_clannfear_separates_player_and_pet_self_heals():
    rows = _repository().get_for_skill_rank(4750)
    by_number = {row.coefficient_number: row for row in rows}

    assert by_number[3].heal_recipient_scope is HealRecipientScope.SELF
    assert by_number[3].heal_recipient_key == "caster"
    assert by_number[3].can_crit is True
    assert by_number[4].heal_recipient_scope is HealRecipientScope.PET
    assert by_number[4].heal_recipient_key == "summoned_pet"
    assert by_number[4].can_crit is True


def test_regenerative_ward_classifies_only_reviewed_self_heal_row():
    shield = SkillComponentClassification(
        skill_rank_id=5123,
        coefficient_number=1,
        effect_kind=SkillEffectKind.SHIELD,
    )
    rows = _repository((shield,)).get_for_skill_rank(5123)
    by_number = {row.coefficient_number: row for row in rows}

    assert by_number[1] is shield
    assert by_number[2].effect_kind is SkillEffectKind.HEAL
    assert by_number[2].heal_recipient_scope is HealRecipientScope.SELF
    assert by_number[2].heal_recipient_key == "caster"
    assert by_number[2].heal_event_key == "cast_direct"
    assert by_number[2].can_crit is True


def test_unrelated_skill_rank_delegates_without_overlay():
    base = SkillComponentClassification(
        skill_rank_id=42,
        coefficient_number=1,
        effect_kind=SkillEffectKind.DAMAGE,
    )

    assert _repository((base,)).get_for_skill_rank(42) == (base,)
