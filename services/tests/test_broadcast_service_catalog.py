from services.service_catalog import (
    ServiceBehavior,
    canonical_service_for,
    get_service,
)


def test_obs_scene_switch_is_external_action_not_stream_event_persistence():
    service = canonical_service_for("broadcast_obs_scene_switch")

    assert service is not None
    assert service.service_id == "broadcast.obs.scene_switch"
    assert service.ui_safe is True
    assert "OBS owns the actual scene switch" in service.notes
    assert "does not own stream event persistence" in service.notes


def test_stream_event_service_uses_sequence_numbers_for_repeated_triggers():
    service = canonical_service_for("broadcast_stream_event_persistence")

    assert service is not None
    assert service.service_id == "broadcast.stream_event.persistence"
    assert "Sequence numbers distinguish repeated trigger requests" in service.notes
    assert "does not itself command OBS scene changes" in service.notes


def test_incident_json_is_record_persistence_not_gameplay_inference():
    service = canonical_service_for("broadcast_incident_json_persistence")

    assert service is not None
    assert service.service_id == "broadcast.incident.persistence"
    assert "not inferred from gameplay evidence" in service.notes


def test_narrator_selection_is_presentation_heuristic_not_mechanics_evidence():
    service = canonical_service_for("broadcast_narrator_content_selection")

    assert service is not None
    assert service.service_id == "broadcast.narrator.content"
    assert service.behavior is ServiceBehavior.HEURISTIC
    assert "random choice" in service.notes
    assert "not mechanics or encounter evidence" in service.notes


def test_icon_loader_is_presentation_only():
    service = canonical_service_for("ui_icon_asset_loading")

    assert service is not None
    assert service.service_id == "ui.icon.assets"
    assert service.ui_safe is True
    assert "presentation-only" in service.notes
    assert "never gameplay evidence" in service.notes


def test_generic_timeline_does_not_become_gameplay_truth_from_timestamps():
    service = canonical_service_for("generic_event_timeline_collection")

    assert service is not None
    assert service.service_id == "timeline.event.collection"
    assert "does not create encounter semantics" in service.notes
    assert "authoritative gameplay timeline" in service.notes


def test_broadcast_utility_capabilities_remain_distinct():
    ids = {
        get_service("broadcast.obs.scene_switch").service_id,
        get_service("broadcast.stream_event.persistence").service_id,
        get_service("broadcast.incident.persistence").service_id,
        get_service("broadcast.narrator.content").service_id,
        get_service("ui.icon.assets").service_id,
        get_service("timeline.event.collection").service_id,
    }

    assert ids == {
        "broadcast.obs.scene_switch",
        "broadcast.stream_event.persistence",
        "broadcast.incident.persistence",
        "broadcast.narrator.content",
        "ui.icon.assets",
        "timeline.event.collection",
    }
