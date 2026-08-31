import json

from importers.eso_logs_critical_adapter import (
    load_eso_logs_events,
    normalize_eso_logs_critical_events,
    write_normalized_observations,
)
from importers.skill_critical_observation_importer import load_runtime_critical_observations
from minmax.skill_critical_observation import CriticalEventFamily


def test_adapter_normalizes_damage_heal_direct_and_periodic_families():
    events = (
        {"type": "damage", "abilityGameID": 1001, "isCritical": True, "isTick": False},
        {"type": "damage", "abilityGameID": 1002, "isCritical": True, "isTick": True},
        {"type": "heal", "abilityGameID": 1003, "isCritical": True, "isTick": False},
        {"type": "healing", "abilityGameID": 1004, "isCritical": True, "isTick": True},
    )

    observations, summary = normalize_eso_logs_critical_events(
        events,
        source="ESO Logs report TEST fight 1",
    )

    assert summary.events_scanned == 4
    assert summary.critical_events == 4
    assert summary.normalized_groups == 4
    assert summary.normalized_critical_events == 4
    assert [(item.ability_id, item.event_family) for item in observations] == [
        (1001, CriticalEventFamily.DAMAGE_DIRECT),
        (1002, CriticalEventFamily.DAMAGE_PERIODIC),
        (1003, CriticalEventFamily.HEAL_DIRECT),
        (1004, CriticalEventFamily.HEAL_PERIODIC),
    ]


def test_adapter_aggregates_duplicate_positive_critical_events():
    events = (
        {"type": "damage", "abilityGameID": 2001, "isCritical": True, "isTick": False},
        {"type": "damage", "abilityGameID": 2001, "isCritical": True, "isTick": False},
        {"type": "damage", "abilityGameID": 2001, "isCritical": True, "isTick": False},
    )

    observations, summary = normalize_eso_logs_critical_events(events, source="ESO Logs test")

    assert len(observations) == 1
    assert observations[0].observed_count == 3
    assert summary.normalized_critical_events == 3


def test_adapter_ignores_noncritical_and_reports_unusable_critical_events():
    events = (
        {"type": "damage", "abilityGameID": 3001, "isCritical": False, "isTick": False},
        {"type": "damage", "isCritical": True, "isTick": False},
        {"type": "cast", "abilityGameID": 3002, "isCritical": True, "isTick": False},
    )

    observations, summary = normalize_eso_logs_critical_events(events, source="ESO Logs test")

    assert observations == ()
    assert summary.skipped_noncritical == 1
    assert summary.critical_events == 2
    assert summary.skipped_missing_ability_id == 1
    assert summary.skipped_unknown_event_type == 1


def test_adapter_reads_nested_ability_game_id():
    events = (
        {
            "type": "damage",
            "ability": {"name": "Fixture", "gameID": 4001},
            "isCritical": True,
            "isTick": False,
        },
    )

    observations, _summary = normalize_eso_logs_critical_events(events, source="ESO Logs test")

    assert observations[0].ability_id == 4001


def test_loader_walks_nested_graphql_event_response(tmp_path):
    path = tmp_path / "events.json"
    path.write_text(
        json.dumps(
            {
                "data": {
                    "reportData": {
                        "report": {
                            "events": {
                                "data": [
                                    {
                                        "type": "damage",
                                        "abilityGameID": 5001,
                                        "isCritical": True,
                                        "isTick": False,
                                    },
                                    {
                                        "type": "heal",
                                        "ability": {"gameID": 5002},
                                        "isCritical": True,
                                        "isTick": True,
                                    },
                                ],
                                "nextPageTimestamp": None,
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    events = load_eso_logs_events(path)

    assert len(events) == 2
    assert events[0]["abilityGameID"] == 5001
    assert events[1]["ability"]["gameID"] == 5002


def test_adapter_output_is_accepted_by_runtime_crit_importer_loader(tmp_path):
    events = (
        {"type": "damage", "abilityGameID": 6001, "isCritical": True, "isTick": False},
        {"type": "damage", "abilityGameID": 6001, "isCritical": True, "isTick": False},
    )
    observations, _summary = normalize_eso_logs_critical_events(
        events,
        source="ESO Logs report PIPELINE fight 2",
    )
    output = tmp_path / "normalized.json"

    write_normalized_observations(output, observations)
    loaded = load_runtime_critical_observations(output)

    assert loaded == observations
    assert loaded[0].observed_count == 2


def test_loader_supports_jsonl_events(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "damage",
                        "abilityID": 7001,
                        "isCritical": True,
                        "isTick": False,
                    }
                ),
                json.dumps(
                    {
                        "type": "heal",
                        "abilityId": 7002,
                        "isCritical": True,
                        "isTick": False,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    events = load_eso_logs_events(path)
    observations, _summary = normalize_eso_logs_critical_events(events, source="ESO Logs JSONL")

    assert [item.ability_id for item in observations] == [7001, 7002]


def test_adapter_requires_provenance_source():
    events = (
        {"type": "damage", "abilityGameID": 8001, "isCritical": True, "isTick": False},
    )

    try:
        normalize_eso_logs_critical_events(events, source="   ")
    except ValueError as exc:
        assert "source is required" in str(exc)
    else:
        raise AssertionError("expected ValueError")
