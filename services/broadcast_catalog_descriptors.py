from __future__ import annotations

"""Broadcast and stream-support service catalog descriptors.

Metadata only. These entries document presentation, trigger, persistence, and OBS
integration boundaries without turning the catalog into a runtime service locator.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


BROADCAST_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="broadcast.obs.scene_switch",
        domain="broadcast",
        purpose="Perform explicit OBS WebSocket v5 program-scene changes with authentication, timeout handling, and success/failure signaling.",
        implementation_path="services.obs_websocket_service",
        inputs=("ObsHost", "ObsPort", "ObsPassword", "SceneName"),
        outputs=("SceneChangedSignal", "FailureSignal"),
        responsibilities=("broadcast_obs_scene_switch",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="OBS owns the actual scene switch through its WebSocket/UI path. This service does not route scene changes through the Lua polling trigger and does not own stream event persistence.",
    ),
    ServiceDescriptor(
        service_id="broadcast.stream_event.persistence",
        domain="broadcast",
        purpose="Write sequence-numbered OBS polling trigger payloads and persist per-stream pull/wipe session state plus append-only boss logs.",
        implementation_path="services.stream_event_service",
        inputs=("StreamEvent", "StreamSession", "BossLogEntry"),
        outputs=("CurrentStreamEventJson", "StreamSessionJson", "BossLog"),
        responsibilities=("broadcast_stream_event_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes="Sequence numbers distinguish repeated trigger requests even when their visible labels are identical. This service persists stream-operation state; it does not itself command OBS scene changes.",
    ),
    ServiceDescriptor(
        service_id="broadcast.incident.persistence",
        domain="broadcast",
        purpose="Load and save the structured broadcast IncidentModel as human-editable JSON.",
        implementation_path="services.incident_json_service",
        inputs=("IncidentJson", "IncidentModel"),
        outputs=("IncidentModel", "IncidentJson"),
        responsibilities=("broadcast_incident_json_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="This is persistence for broadcast incident records only. Responsible-party and status flags are stored exactly as model state and are not inferred from gameplay evidence.",
    ),
    ServiceDescriptor(
        service_id="broadcast.narrator.content",
        domain="broadcast",
        purpose="Load categorized Natural History narrator copy from JSON or Markdown and choose one entry for a requested category.",
        implementation_path="services.narrator_service",
        inputs=("NarratorContent", "NarratorCategory"),
        outputs=("NarratorCategories", "NarratorText"),
        responsibilities=("broadcast_narrator_content_selection",),
        behavior=ServiceBehavior.HEURISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Category parsing is deterministic, but pick() intentionally uses random choice among available authored lines. Narrator copy is presentation content, not mechanics or encounter evidence.",
    ),
    ServiceDescriptor(
        service_id="ui.icon.assets",
        domain="ui",
        purpose="Resolve named SVG assets from the FoundryDock icon directory into Qt icons for UI consumers.",
        implementation_path="services.icon_service",
        inputs=("IconName",),
        outputs=("QIcon",),
        responsibilities=("ui_icon_asset_loading",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Icon lookup is presentation-only. A missing file is reported and still returns a Qt icon object for the requested path; icon presence is never gameplay evidence.",
    ),
    ServiceDescriptor(
        service_id="timeline.event.collection",
        domain="timeline",
        purpose="Maintain typed Event objects in chronological order, filter them by explicit fields/time bounds, and export the resulting timeline as JSON.",
        implementation_path="services.timeline_service",
        inputs=("Event", "EventFilter", "TimeBounds"),
        outputs=("OrderedEvents", "TimelineJson"),
        responsibilities=("generic_event_timeline_collection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="This is a generic event container/export utility. It does not create encounter semantics, infer event meaning, or become an authoritative gameplay timeline merely because events are timestamped.",
    ),
)


__all__ = ["BROADCAST_SERVICE_DESCRIPTORS"]
