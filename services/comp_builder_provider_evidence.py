from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.comp_builder_build_candidates import CompBuildCandidate
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.raid_coverage_encounter_adapter import RaidCoverageEncounterAdapter
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE, RaidCoverageProfile
from services.saved_build_capability_service import SavedBuildCapabilityService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class CompProviderRequirementResolution:
    provider_ids: tuple[str, ...]
    unresolved: tuple[str, ...] = ()


class CompBuilderProviderEvidenceService:
    """Resolve Comp Maker provider evidence through existing canonical Phase 10/11 data.

    Display labels are matched only to explicit rows in the raid coverage profile.
    A row is enforceable only when that profile row already has a canonical capability
    mapping. Unmapped labels remain unresolved; this service never infers capability
    identity from gear names, skill names, or prose.
    """

    def __init__(
        self,
        data_dir: str | Path,
        *,
        profile: RaidCoverageProfile = DEFAULT_RAID_COVERAGE_PROFILE,
        capability_service: SavedBuildCapabilityService | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.profile = profile
        self.coverage_adapter = RaidCoverageEncounterAdapter(profile)
        self.capability_adapter = SavedBuildEncounterCapabilityAdapter(
            self.coverage_adapter.capability_identity_maps()
        )
        self.build_service = BuildService(self.data_dir / "builds.json")
        self.capability_service = capability_service or SavedBuildCapabilityService(
            self.build_service,
            self.data_dir / "eso.db",
        )
        self._rows_by_label = {
            row.display_name.casefold(): row
            for row in profile.requirements
        }
        self._candidate_provider_cache: dict[str, tuple[str, ...]] = {}

    def resolve_requirement_labels(
        self,
        labels: tuple[str, ...],
    ) -> CompProviderRequirementResolution:
        provider_ids: list[str] = []
        unresolved: list[str] = []
        for raw in labels:
            label = _clean(raw)
            if not label:
                continue
            row = self._rows_by_label.get(label.casefold())
            if row is None:
                unresolved.append(
                    f"provider requirement is not in the canonical raid coverage profile: {label}"
                )
                continue
            if row.capability_type is None:
                unresolved.append(
                    f"provider requirement has no proven canonical capability mapping yet: {row.display_name}"
                )
                continue
            provider_ids.append(row.capability_type)
        return CompProviderRequirementResolution(
            provider_ids=tuple(dict.fromkeys(provider_ids)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def provider_ids_for_build(self, build: PlayerBuild) -> tuple[str, ...]:
        mapped = self.profile.mapped_required
        if not mapped:
            return ()
        audit = self.capability_service.audit_build(build)
        capability_types = tuple(row.capability_type for row in mapped if row.capability_type)
        evidence = self.capability_adapter.evidence_for((audit,), capability_types)
        supported = {
            row.capability_type
            for row in evidence
            if row.assessment.value == "supported"
        }
        return tuple(
            row.capability_type
            for row in mapped
            if row.capability_type in supported
        )

    def provider_ids_for_candidate(self, candidate: CompBuildCandidate) -> tuple[str, ...]:
        """Return only canonically proven provider identities for one candidate.

        Saved BFF builds can be reloaded as complete canonical build snapshots and
        audited through SavedBuildCapabilityService. Reference/observed templates
        are not treated as providers here because CompBuildCandidate intentionally
        carries only partial build evidence and cannot prove the full configured
        build needed by the capability audit.
        """

        if candidate.source_kind != "saved_build":
            return ()
        cached = self._candidate_provider_cache.get(candidate.candidate_id)
        if cached is not None:
            return cached

        target_name = _clean(candidate.name).casefold()
        target_owner = _clean(candidate.source_name).casefold()
        matches: list[PlayerBuild] = []
        for build in self.build_service.load().Members:
            build_name = _clean(build.BuildName).casefold()
            owner = (_clean(build.Name) or _clean(build.Gamertag)).casefold()
            if build_name == target_name and owner == target_owner:
                matches.append(build)

        if len(matches) != 1:
            # Ambiguous or stale candidate identity must remain unresolved instead
            # of borrowing provider evidence from a different saved build.
            result: tuple[str, ...] = ()
        else:
            result = self.provider_ids_for_build(matches[0])
        self._candidate_provider_cache[candidate.candidate_id] = result
        return result
