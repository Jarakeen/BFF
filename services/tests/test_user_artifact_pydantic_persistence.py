from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.antiquity_progress_pydantic_schema import validate_antiquity_progress_document
from services.user_artifact_pydantic_schema import (
    validate_performance_focus_document,
    validate_rotation_artifact_document,
)


def test_antiquity_progress_rejects_nonpositive_ids() -> None:
    with pytest.raises(ValueError):
        validate_antiquity_progress_document({
            "schema_version": 1,
            "profiles": {"Default": {"0": {"recovered": True, "recovered_on": "", "notes": ""}}},
        })


def test_antiquity_progress_rejects_duplicate_profile_identity() -> None:
    with pytest.raises(ValueError):
        validate_antiquity_progress_document({
            "schema_version": 1,
            "profiles": {"Raid Lead": {}, "raid lead": {}},
        })


def test_rotation_artifact_document_requires_actions() -> None:
    with pytest.raises(ValueError):
        validate_rotation_artifact_document({
            "schema_version": 1,
            "rotations": {"build-1": {"actions": []}},
        })


def test_performance_focus_rejects_out_of_range_percent() -> None:
    with pytest.raises(ValueError):
        validate_performance_focus_document({
            "Goals": [{
                "Name": "Major Slayer",
                "TargetPercent": 101.0,
                "CurrentPercent": None,
                "Source": "Custom",
                "ReportCode": "",
                "FightId": "",
                "FightName": "",
                "ActorLabel": "",
                "Role": "",
                "EvidenceNote": "",
            }]
        })


def test_performance_focus_rejects_more_than_eight_goals() -> None:
    goals = [{
        "Name": f"Goal {index}",
        "TargetPercent": 50.0,
        "CurrentPercent": None,
        "Source": "Custom",
        "ReportCode": "",
        "FightId": "",
        "FightName": "",
        "ActorLabel": "",
        "Role": "",
        "EvidenceNote": "",
    } for index in range(9)]
    with pytest.raises(ValueError):
        validate_performance_focus_document({"Goals": goals})
