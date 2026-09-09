from __future__ import annotations

"""Stable application-domain service catalog descriptors.

Metadata only. These descriptors cover mature app services outside the active
Rotation, Performance, and Extreme workstreams. Runtime code continues to use typed
imports and explicit wiring.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


APPLICATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="collectible.antiquity.progress",
        domain="collectible",
        purpose="Expose the harvested UESP Antiquities reference catalog together with profile-specific recovered state and notes.",
        implementation_path="services.antiquity_service",
        inputs=("UESPAntiquityCsv", "AntiquityProgressProfile"),
        outputs=("AntiquityCatalogItem", "AntiquityProgressSummary"),
        responsibilities=("antiquity_reference_and_profile_progress",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        provenance=("UESP antiquityLeads export", "local profile progress"),
        notes="Reference rows and user progress are distinct concerns within one UI-facing service. The catalog is considered available only when the expected harvested row count is complete and source ids are unique; profile progress never rewrites the reference rows.",
    ),
    ServiceDescriptor(
        service_id="broadcast.expedition.session_state",
        domain="broadcast",
        purpose="Maintain the active in-memory Expedition and its chronological event collection for the current application/streaming session.",
        implementation_path="services.expedition_service",
        inputs=("Event",),
        outputs=("ExpeditionModel",),
        responsibilities=("active_expedition_session_state",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="This is transient active-session state, not durable archive persistence and not canonical encounter truth. Starting or resetting an Expedition creates a new in-memory event collection.",
    ),
    ServiceDescriptor(
        service_id="broadcast.raid.progress_events",
        domain="broadcast",
        purpose="Record pull, wipe, clear, and Ult-pull events into the active Expedition and summarize that session's raid progression events.",
        implementation_path="services.raid_service",
        inputs=("ExpeditionService", "RaidProgressEvent"),
        outputs=("Event", "RaidSessionSummary"),
        dependencies=("broadcast.expedition.session_state",),
        responsibilities=("active_raid_progress_event_recording",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="RaidService records operator/session events only. Wipe percentages and pull counts are session observations supplied by the caller; they are not encounter mechanics or performance evidence unless another layer explicitly validates them.",
    ),
    ServiceDescriptor(
        service_id="logs.top_team.observed_build_evidence",
        domain="logs",
        purpose="Read a bounded top-ranked encounter report from ESO Logs as reusable observed team/build evidence, with lazy Mundus resolution from aura uptime.",
        implementation_path="services.top_team_service",
        inputs=("EsoLogsClient", "EncounterId", "RankedReport"),
        outputs=("TopTeamResult", "TopTeamPlayer"),
        responsibilities=("esologs_top_team_observed_build_evidence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("ESO Logs ranked reports", "ESO Logs playerDetails", "ESO Logs aura uptime"),
        notes="This service exposes observed ranked-log evidence, not canonical optimal composition. Class, gear names, abilities, and Mundus are observations from a selected report; absence or popularity must not be promoted into game-mechanic truth.",
    ),
    ServiceDescriptor(
        service_id="logs.trending.observed_role_meta",
        domain="logs",
        purpose="Aggregate bounded top individual ESO Logs character rankings into role-specific observed gear-set, class, and player-loadout popularity summaries.",
        implementation_path="services.esologs_trending_service",
        inputs=("EsoLogsClient", "EncounterId", "RankedCharacterSample"),
        outputs=("EsoLogsTrendingReport", "RoleTrendingSummary", "TrendingItem"),
        dependencies=("logs.top_team.observed_build_evidence",),
        responsibilities=("esologs_ranked_role_trending_evidence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("ESO Logs characterRankings", "ESO Logs playerDetails"),
        notes="Popularity is descriptive observational evidence only. Set counts are per matched top-ranked individual player, never per full team or equipped item. Ranked identities that cannot be matched exactly back to playerDetails are skipped rather than guessed. This is not canonical best-in-slot evidence: neither frequency nor absence establishes mechanic truth.",
    ),
    ServiceDescriptor(
        service_id="build.skill_choice.reference",
        domain="build",
        purpose="Load one representative database row per base/morph skill choice and apply explicit skill-bar eligibility filters for UI selection.",
        implementation_path="services.skill_choice_service",
        inputs=("EsoDatabase", "CharacterClass", "SlotIndex", "TransformationState"),
        outputs=("SkillChoice", "EligibleSkillChoice"),
        responsibilities=("skill_bar_choice_reference_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Representative numeric ability ids identify exact imported source rows for downstream lookup; they are aliases/evidence only and never replace BFF's canonical semantic lower_snake_case skill identity. Eligibility remains an explicit projection over database facts and transformation state.",
    ),
)


__all__ = ["APPLICATION_SERVICE_DESCRIPTORS"]
