from __future__ import annotations

"""Derive Rotation Builder Tank context from assignment-backed evidence on demand."""

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from models.build_model import PlayerBuild
from services.encounter_boss_guide import EncounterBossGuide
from services.encounter_evidence import ReconciledEncounterFact
from services.encounter_provider_assignment import ProviderAssignment
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
)
from services.rotation_assignment_taunt_obligation_service import (
    RotationAssignmentTauntPolicy,
)
from services.rotation_tank_assignment_obligation_bundle_service import (
    RotationTankAssignmentObligationBundleService,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)
from services.rotation_tank_encounter_defensive_bundle_service import (
    RotationTankEncounterDefensiveBundleService,
)
from services.rotation_tank_encounter_defensive_timing_service import (
    RotationTankEncounterDefensiveTimingPolicy,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
from ui.rotation_generate_tank_role_evidence_support import (
    RotationGenerateTankObligationContext,
)


@dataclass(frozen=True)
class RotationGenerateTankAssignmentEvidence:
    """Exact assignment and reviewed defensive evidence for one member/encounter.

    Defensive obligations may be supplied directly for explicit audit/test callers, or
    derived from reviewed encounter facts plus reviewed explicit-clock timing policy.
    The two paths are mutually exclusive so one mechanic never acquires competing truths.
    """

    encounter_id: str
    member_id: str
    assignments: tuple[ProviderAssignment, ...] = ()
    taunt_policies: tuple[RotationAssignmentTauntPolicy, ...] = ()
    taunt_maintenance_policies: tuple[
        RotationAssignmentTauntMaintenancePolicy, ...
    ] = ()
    defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = ()
    defensive_guide: EncounterBossGuide | None = None
    defensive_facts: tuple[ReconciledEncounterFact, ...] = ()
    defensive_timing_policies: tuple[
        RotationTankEncounterDefensiveTimingPolicy, ...
    ] = ()

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        member_id = str(self.member_id or "").strip()
        if not encounter_id:
            raise ValueError("Tank Generate assignment evidence requires encounter_id")
        if not member_id:
            raise ValueError("Tank Generate assignment evidence requires member_id")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "member_id", member_id)
        object.__setattr__(self, "assignments", tuple(self.assignments))
        object.__setattr__(self, "taunt_policies", tuple(self.taunt_policies))
        object.__setattr__(
            self,
            "taunt_maintenance_policies",
            tuple(self.taunt_maintenance_policies),
        )
        object.__setattr__(
            self,
            "defensive_obligations",
            tuple(self.defensive_obligations),
        )
        object.__setattr__(self, "defensive_facts", tuple(self.defensive_facts))
        object.__setattr__(
            self,
            "defensive_timing_policies",
            tuple(self.defensive_timing_policies),
        )

        has_reviewed_defensive_inputs = bool(
            self.defensive_guide
            or self.defensive_facts
            or self.defensive_timing_policies
        )
        if self.defensive_obligations and has_reviewed_defensive_inputs:
            raise ValueError(
                "Tank Generate defensive evidence must use either explicit obligations or reviewed encounter projection, not both"
            )
        if has_reviewed_defensive_inputs:
            if self.defensive_guide is None:
                raise ValueError(
                    "Tank Generate reviewed defensive evidence requires defensive_guide"
                )
            guide_encounter = str(
                getattr(self.defensive_guide, "encounter_id", "") or ""
            ).strip()
            if guide_encounter.casefold() != encounter_id.casefold():
                raise ValueError(
                    "Tank Generate defensive guide encounter does not match assignment evidence encounter"
                )
            if not self.defensive_timing_policies:
                raise ValueError(
                    "Tank Generate reviewed defensive evidence requires timing policies"
                )


class RotationGenerateTankAssignmentContextSupport:
    """Resolve the selected Tank build/encounter into exact hard obligations."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        build_adapter: SavedBuildCharacterAdapter | object | None = None,
        bundle_service: RotationTankAssignmentObligationBundleService | object | None = None,
        defensive_bundle_service: RotationTankEncounterDefensiveBundleService | object | None = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(self.database_path)
        self.bundle_service = (
            bundle_service or RotationTankAssignmentObligationBundleService()
        )
        self.defensive_bundle_service = (
            defensive_bundle_service or RotationTankEncounterDefensiveBundleService()
        )
        self._evidence: tuple[RotationGenerateTankAssignmentEvidence, ...] = ()

    def set_evidence(
        self,
        evidence: tuple[RotationGenerateTankAssignmentEvidence, ...],
    ) -> None:
        rows = tuple(evidence)
        seen: set[tuple[str, str]] = set()
        for row in rows:
            if not isinstance(row, RotationGenerateTankAssignmentEvidence):
                raise TypeError(
                    "Tank Generate assignment evidence rows must be "
                    "RotationGenerateTankAssignmentEvidence"
                )
            key = (row.encounter_id.casefold(), row.member_id.casefold())
            if key in seen:
                raise ValueError(
                    "duplicate Tank Generate assignment evidence for encounter/member: "
                    f"{row.encounter_id!r} / {row.member_id!r}"
                )
            seen.add(key)
        self._evidence = rows

    def context_for(
        self,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationGenerateTankObligationContext | None:
        encounter_id = str(evidence_bundle.encounter_id or "").strip()
        matches = tuple(
            row
            for row in self._evidence
            if row.encounter_id.casefold() == encounter_id.casefold()
        )
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                "multiple Tank assignment evidence rows match selected encounter; "
                "member identity must be unambiguous"
            )
        row = matches[0]

        adaptation = self.build_adapter.adapt(player_build)
        unresolved = tuple(
            str(item).strip()
            for item in getattr(adaptation, "unresolved", ())
            if str(item).strip()
        )
        build = getattr(adaptation, "build", None)
        if build is None or unresolved:
            detail = "; ".join(unresolved) or "canonical build unavailable"
            raise ValueError(
                "cannot derive Tank assignment obligations because saved-build adaptation "
                "is unresolved: " + detail
            )

        defensive_obligations = self._defensive_obligations(row)
        bundle = self.bundle_service.compose(
            build=build,
            member_id=row.member_id,
            encounter_id=encounter_id,
            assignments=row.assignments,
            taunt_policies=row.taunt_policies,
            taunt_maintenance_policies=row.taunt_maintenance_policies,
            defensive_obligations=defensive_obligations,
        )
        return RotationGenerateTankObligationContext(
            encounter_id=bundle.encounter_id,
            taunt_application_requirements=bundle.taunt_application_requirements,
            taunt_maintenance_requirements=bundle.taunt_maintenance_requirements,
            defensive_obligations=bundle.defensive_obligations,
        )

    def _defensive_obligations(
        self,
        row: RotationGenerateTankAssignmentEvidence,
    ) -> tuple[RotationTankDefensiveObligation, ...]:
        if row.defensive_obligations:
            return row.defensive_obligations
        if row.defensive_guide is None:
            return ()

        projection = self.defensive_bundle_service.project(
            guide=row.defensive_guide,
            facts=row.defensive_facts,
            policies=row.defensive_timing_policies,
        )
        unresolved = tuple(
            str(item).strip()
            for item in getattr(projection, "unresolved", ())
            if str(item).strip()
        )
        if unresolved:
            raise ValueError(
                "cannot derive Tank defensive obligations from reviewed encounter evidence: "
                + "; ".join(unresolved)
            )
        obligations = tuple(getattr(projection, "obligations", ()))
        if not obligations:
            raise ValueError(
                "cannot derive Tank defensive obligations from reviewed encounter evidence: no resolved obligations"
            )
        return obligations

    def install(self, page) -> None:
        page.set_rotation_generate_tank_assignment_evidence = self.set_evidence
        page.rotation_generate_tank_assignment_context = self.context_for


__all__ = [
    "RotationGenerateTankAssignmentContextSupport",
    "RotationGenerateTankAssignmentEvidence",
]
