from __future__ import annotations

"""Scribing-domain service catalog descriptors.

Metadata only. These entries document verified result-name lookup, simulator
compatibility filtering, and the versioned Update 51 PTS reference reader without
turning any external/public source into universal canonical game truth.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceAuthority,
    ServiceBehavior,
    ServiceDescriptor,
)


SCRIBING_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="scribing.result_name_resolution",
        domain="scribing",
        purpose="Resolve verified Grimoire + Focus result names from stored evidence, preferring probe-verified ESO client captures and falling back to separately verified public reference data.",
        implementation_path="services.scribing_result_service",
        inputs=("EsoDatabase", "GrimoireName", "FocusScriptName"),
        outputs=("ScribingResultName", "ScribingResultSourceMetadata"),
        responsibilities=("scribing_verified_result_name_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("Probe-verified ESO client capture or separately verified public scribing reference",),
        notes="Verified ESO client capture takes precedence. Public simulator/API rows are fallback evidence only and are never promoted above a verified client source merely because they are structured or convenient.",
    ),
    ServiceDescriptor(
        service_id="scribing.simulator_compatibility",
        domain="scribing",
        purpose="Expose verified structured Grimoire/script compatibility and forbidden-combination filtering for the current Scribing Simulator UI, with the older static catalog used only when structured simulator data is unavailable.",
        implementation_path="services.scribing_simulator_data_service",
        inputs=("EsoDatabase", "GrimoireName", "SelectedScripts"),
        outputs=("CompatibleFocusScripts", "CompatibleSignatureScripts", "CompatibleAffixScripts", "CombinationAllowed"),
        responsibilities=("scribing_simulator_compatibility_filtering",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("Probe-verified structured ESO-Hub Scribing simulator initialization payload",),
        notes="Structured verified simulator data owns current filtering when available. The static catalog is a compatibility fallback, and malformed singleton forbidden rules are not allowed to disable otherwise valid scripts globally.",
    ),
    ServiceDescriptor(
        service_id="scribing.u51_pts_reference",
        domain="scribing",
        purpose="Read the normalized Update 51 PTS scribing snapshot, including script-slot compatibility and class-aware crafted-script descriptions, as versioned reference evidence.",
        implementation_path="services.scribing_u51_service",
        inputs=("EsoDatabase", "GrimoireName", "ScriptName", "ClassId"),
        outputs=("U51ScribingResolution", "CompatibleScripts"),
        responsibilities=("scribing_u51_pts_reference_lookup",),
        authority=ServiceAuthority.EXPERIMENTAL,
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        provenance=("UESP ESO Log Update 51 PTS scribing exports",),
        notes="This is an explicitly versioned PTS snapshot, not a live-version authority and not an automatic successor to the current Scribing Simulator services. Numeric ability ids remain source evidence, not canonical semantic skill identity.",
    ),
)


__all__ = ["SCRIBING_SERVICE_DESCRIPTORS"]
