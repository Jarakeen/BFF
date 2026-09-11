from __future__ import annotations

import json

import pytest

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse
from tools.rotation_runtime_snapshot_fixture import (
    load_rotation_runtime_snapshot_fixture,
)


def _write(tmp_path, payload):
    path = tmp_path / "runtime_snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loads_authoritative_runtime_history_without_inference(tmp_path):
    snapshot = load_rotation_runtime_snapshot_fixture(
        _write(
            tmp_path,
            {
                "snapshot_time_seconds": 12.0,
                "recipient_actor_id": "healer",
                "group_member_ids": ["healer", "support"],
                "runtime_history": [
                    {
                        "kind": "effect_attempt",
                        "time_seconds": 2.0,
                        "sequence": 4,
                        "trigger": "skill_cast",
                        "source": "Budding Seeds",
                        "target": "group",
                        "chance_roll": 0.25,
                    },
                    {
                        "kind": "potion_use",
                        "time_seconds": 5.0,
                        "sequence": 1,
                    },
                    {
                        "kind": "external_group_buff",
                        "source_actor_id": "support",
                        "recipient_actor_id": "healer",
                        "buff_name": "major courage",
                        "target_type": "group",
                        "applied_at_seconds": 8.0,
                        "duration_seconds": 10.0,
                        "source_evidence": "reviewed log fixture",
                        "sequence": 2,
                    },
                ],
            },
        )
    )

    assert snapshot.snapshot_time_seconds == 12.0
    assert snapshot.recipient_actor_id == "healer"
    assert snapshot.group_member_ids == ("healer", "support")
    assert len(snapshot.runtime_history) == 3

    attempt = next(
        item
        for item in snapshot.runtime_history
        if isinstance(item, RuntimeEffectEventAttempt)
    )
    assert attempt.event.time_seconds == 2.0
    assert attempt.event.sequence == 4
    assert attempt.event.trigger == "skill_cast"
    assert attempt.event.source == "Budding Seeds"
    assert attempt.chance_roll == pytest.approx(0.25)

    potion = next(
        item
        for item in snapshot.runtime_history
        if isinstance(item, ExtremeRuntimePotionUse)
    )
    assert potion.time_seconds == 5.0

    external = next(
        item
        for item in snapshot.runtime_history
        if isinstance(item, ExternalGroupBuffApplication)
    )
    assert external.source_actor_id == "support"
    assert external.recipient_actor_id == "healer"
    assert external.buff_name == "major courage"
    assert external.applied_at_seconds == 8.0
    assert external.duration_seconds == 10.0


def test_rejects_condition_context_in_audit_fixture(tmp_path):
    path = _write(
        tmp_path,
        {
            "runtime_history": [
                {
                    "kind": "effect_attempt",
                    "time_seconds": 1.0,
                    "trigger": "skill_cast",
                    "source": "Test Skill",
                    "condition_context": {"invented": True},
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="does not reconstruct condition_context"):
        load_rotation_runtime_snapshot_fixture(path)


def test_rejects_unknown_runtime_history_kind(tmp_path):
    path = _write(
        tmp_path,
        {
            "runtime_history": [
                {
                    "kind": "mystery_event",
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="unsupported kind"):
        load_rotation_runtime_snapshot_fixture(path)
