from __future__ import annotations

"""Conservative bridge from saved-build EffectVariant audits into Phase 10 evidence.

Capability recognition uses exact EffectVariant.name identities supplied by an
audited mapping. This module never guesses from skill/source names or prose.
Canonical character identity is preferred over display labels so roster evidence
survives renames and cannot silently treat two builds for one character as two
independent providers.
"""

from dataclasses import dataclass

from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    RosterCapabilityEvidence,
)
from services.saved_build_capability_service import SavedBuildCapabilityAudit


@dataclass(frozen=True)
class EncounterCapabilityIdentityMap:
    """Exact effect identities that prove one encounter capability."""

    capability_type: str
    effect_names: frozenset[str]

    def __post_init__(self) -> None:
        if not self.capability_type:
            raise ValueError("capability_type must be non-empty")
        if any(not name for name in self.effect_names):
            raise ValueError("effect_names cannot contain empty identities")


class SavedBuildEncounterCapabilityAdapter:
    """Translate resolved saved-build effects into explicit Phase 10 evidence."""

    def __init__(
        self,
        identity_maps: tuple[EncounterCapabilityIdentityMap, ...],
    ) -> None:
        capabilities = [entry.capability_type for entry in identity_maps]
        if len(capabilities) != len(set(capabilities)):
            raise ValueError("identity_maps cannot duplicate capability_type")
        self._maps = {entry.capability_type: entry.effect_names for entry in identity_maps}

    @staticmethod
    def member_id(audit: SavedBuildCapabilityAudit) -> str:
        """Return stable roster identity, falling back only for legacy fixtures."""
        member_id = audit.character_id or audit.character_name or audit.build_name
        if not member_id:
            raise ValueError("saved-build capability audit has no usable member identity")
        return member_id

    def evidence_for(
        self,
        audits: tuple[SavedBuildCapabilityAudit, ...],
        capability_types: tuple[str, ...],
    ) -> tuple[RosterCapabilityEvidence, ...]:
        if len(capability_types) != len(set(capability_types)):
            raise ValueError("capability_types must be unique")
        if any(not capability_type for capability_type in capability_types):
            raise ValueError("capability_types must be non-empty")

        rows: list[RosterCapabilityEvidence] = []
        for audit in audits:
            member_id = self.member_id(audit)

            effects_by_name = {}
            for effect in audit.resolved_effects:
                effects_by_name.setdefault(effect.name, []).append(effect)

            for capability_type in capability_types:
                mapped_names = self._maps.get(capability_type)
                if mapped_names is None or not mapped_names:
                    rows.append(
                        RosterCapabilityEvidence(
                            member_id=member_id,
                            capability_type=capability_type,
                            assessment=CapabilityAssessment.UNKNOWN,
                            source="no audited capability identity mapping",
                        )
                    )
                    continue

                matched = [
                    effect
                    for effect_name in mapped_names
                    for effect in effects_by_name.get(effect_name, ())
                ]
                if any(effect.eligible for effect in matched):
                    matched_sources = ", ".join(
                        dict.fromkeys(effect.source for effect in matched if effect.eligible)
                    )
                    rows.append(
                        RosterCapabilityEvidence(
                            member_id=member_id,
                            capability_type=capability_type,
                            assessment=CapabilityAssessment.SUPPORTED,
                            source=matched_sources or "resolved EffectVariant",
                        )
                    )
                    continue

                if matched:
                    rows.append(
                        RosterCapabilityEvidence(
                            member_id=member_id,
                            capability_type=capability_type,
                            assessment=CapabilityAssessment.UNKNOWN,
                            source="mapped effect exists but current eligibility is unresolved/false",
                        )
                    )
                    continue

                if audit.unresolved:
                    rows.append(
                        RosterCapabilityEvidence(
                            member_id=member_id,
                            capability_type=capability_type,
                            assessment=CapabilityAssessment.UNKNOWN,
                            source="saved-build capability audit has unresolved evidence",
                        )
                    )
                    continue

                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.UNSUPPORTED,
                        source="fully resolved saved build lacks mapped effect identity",
                    )
                )

        return tuple(rows)
