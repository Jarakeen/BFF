from __future__ import annotations

import pytest

from minmax.external_group_buff_provenance import (
    ExternalGroupBuffApplication,
    ExternalGroupBuffProvenanceResolver,
)
from minmax.support_target_type import SupportTargetType


def _application(**overrides):
    values = {
        "source_actor_id": "healer_2",
        "recipient_actor_id": "healer_1",
        "buff_name": "Major Courage",
        "target_type": SupportTargetType.SELF_OR_ALLY,
        "applied_at_seconds": 10.0,
        "duration_seconds": 5.0,
        "source_evidence": "Spell Power Cure runtime application",
    }
    values.update(overrides)
    return ExternalGroupBuffApplication(**values)


def test_external_buff_requires_canonical_named_buff_and_source_evidence() -> None:
    with pytest.raises(ValueError, match="not canonical"):
        _application(buff_name="Definitely Not A Real Buff")
    with pytest.raises(ValueError, match="source evidence"):
        _application(source_evidence="")


def test_external_ally_buff_projects_only_inside_proven_window() -> None:
    resolver = ExternalGroupBuffProvenanceResolver()
    application = _application()

    active = resolver.resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
        snapshot_time_seconds=12.0,
        applications=(application,),
    )
    expired = resolver.resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
        snapshot_time_seconds=15.0,
        applications=(application,),
    )

    assert active.active_buffs == ("Major Courage",)
    assert active.unresolved == ()
    assert expired.active_buffs == ()


def test_ally_target_rejects_self_application() -> None:
    result = ExternalGroupBuffProvenanceResolver().resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
        snapshot_time_seconds=12.0,
        applications=(
            _application(
                source_actor_id="healer_1",
                target_type=SupportTargetType.ALLY,
            ),
        ),
    )

    assert result.active_buffs == ()
    assert any("recipient is not legal" in item for item in result.unresolved)


def test_self_target_rejects_external_source() -> None:
    result = ExternalGroupBuffProvenanceResolver().resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
        snapshot_time_seconds=12.0,
        applications=(_application(target_type=SupportTargetType.SELF),),
    )

    assert result.active_buffs == ()
    assert result.unresolved


def test_group_target_requires_recipient_membership() -> None:
    result = ExternalGroupBuffProvenanceResolver().resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_2",),
        snapshot_time_seconds=12.0,
        applications=(_application(target_type=SupportTargetType.GROUP),),
    )

    assert result.active_buffs == ()
    assert result.unresolved


def test_enemy_target_never_projects_as_friendly_buff() -> None:
    result = ExternalGroupBuffProvenanceResolver().resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
        snapshot_time_seconds=12.0,
        applications=(_application(target_type=SupportTargetType.ENEMY),),
    )

    assert result.active_buffs == ()
    assert result.unresolved


def test_duplicate_proven_applications_collapse_to_one_named_buff() -> None:
    result = ExternalGroupBuffProvenanceResolver().resolve(
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2", "tank_1"),
        snapshot_time_seconds=12.0,
        applications=(
            _application(),
            _application(source_actor_id="tank_1", source_evidence="second proven source"),
        ),
    )

    assert result.active_buffs == ("Major Courage",)
    assert result.unresolved == ()
