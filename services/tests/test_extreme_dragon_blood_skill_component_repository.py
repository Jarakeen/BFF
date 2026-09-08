from __future__ import annotations

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)


class _BaseRepository:
    def __init__(self, rows=()):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, _skill_rank_id):
        return self.rows


def test_dragon_blood_direct_self_heal_identity_is_reviewed():
    repository = ExtremeDragonBloodSkillComponentRepository(
        "ignored.db",
        base_repository=_BaseRepository(),
    )

    rows = repository.get_for_skill_rank(5397)

    assert len(rows) == 1
    row = rows[0]
    assert row.coefficient_number == 1
    assert row.effect_kind is SkillEffectKind.HEAL
    assert row.can_crit is True
    assert row.heal_recipient_scope is HealRecipientScope.SELF
    assert row.heal_temporal_scope is HealTemporalScope.DIRECT
    assert row.heal_recipient_key == "caster"
    assert row.heal_event_key == "cast_direct"


def test_green_dragon_blood_keeps_periodic_total_out_of_one_event_identity():
    repository = ExtremeDragonBloodSkillComponentRepository(
        "ignored.db",
        base_repository=_BaseRepository(),
    )

    rows = repository.get_for_skill_rank(5398)
    by_number = {row.coefficient_number: row for row in rows}

    assert by_number[1].heal_temporal_scope is HealTemporalScope.DIRECT
    assert by_number[1].heal_event_key == "cast_direct"
    assert by_number[2].effect_kind is SkillEffectKind.HEAL
    assert by_number[2].is_dot is True
    assert by_number[2].heal_recipient_scope is HealRecipientScope.SELF
    assert by_number[2].heal_temporal_scope is HealTemporalScope.PERIODIC
    assert by_number[2].heal_event_key is None


def test_elder_dragon_blood_separates_self_and_nearby_allies():
    repository = ExtremeDragonBloodSkillComponentRepository(
        "ignored.db",
        base_repository=_BaseRepository(),
    )

    rows = repository.get_for_skill_rank(5399)
    by_number = {row.coefficient_number: row for row in rows}

    assert by_number[1].is_aoe is False
    assert by_number[1].heal_recipient_scope is HealRecipientScope.SELF
    assert by_number[1].heal_recipient_key == "caster"
    assert by_number[2].is_aoe is True
    assert by_number[2].heal_recipient_scope is HealRecipientScope.GROUP
    assert by_number[2].heal_recipient_key == "nearby_allies"
    assert by_number[1].heal_event_key == by_number[2].heal_event_key == "cast_direct"


def test_reviewed_overlay_preserves_unrelated_base_fields():
    base = SkillComponentClassification(
        skill_rank_id=5399,
        coefficient_number=1,
        effect_kind=SkillEffectKind.UNKNOWN,
        damage_type="legacy-marker",
        source="old source",
    )
    repository = ExtremeDragonBloodSkillComponentRepository(
        "ignored.db",
        base_repository=_BaseRepository((base,)),
    )

    row = repository.get_component(5399, 1)

    assert row is not None
    assert row.damage_type == "legacy-marker"
    assert row.effect_kind is SkillEffectKind.HEAL
    assert row.heal_recipient_key == "caster"


def test_unrelated_skill_rank_delegates_without_overlay():
    base = SkillComponentClassification(
        skill_rank_id=42,
        coefficient_number=3,
        effect_kind=SkillEffectKind.DAMAGE,
    )
    repository = ExtremeDragonBloodSkillComponentRepository(
        "ignored.db",
        base_repository=_BaseRepository((base,)),
    )

    assert repository.get_for_skill_rank(42) == (base,)
