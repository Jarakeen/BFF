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
from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
    RotationAssignmentTauntMaintenanceHorizonPolicyService,
)
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
)
from services.rotation_assignment_taunt_obligation_service import (
    RotationAssignmentTauntPolicy,
)
from services.rotation_tank_assignment_obligation_bundle_service import (
    RotationTankAssignmentObligationBundleService,
)
from services.rotation_tank_defensive_candidate_service import (
    RotationTankDefensiveActionClaim,
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
from services.rotation_tank_encounter_horizon_service import (
    RotationTankEncounterHorizonService,
)
from services.rotation_tank_encounter_threshold_defensive_bundle_service import (
    RotationTankEncounterThresholdDefensiveBundleService,
)
from services.rotation_tank_encounter_threshold_defensive_timing_service import (
    RotationTankEncounterThresholdDefensiveTimingPolicy,
)
from services.rotation_tank_encounter_transition_timing_service import (
    RotationTankEncounterTransitionTimingService,
)
from services.rotation_tank_taunt_candidate_service import (
    RotationTankTauntActionClaim,
)
from services.rotation_tank_taunt_maintenance_candidate_service import (
    RotationTankTauntMaintenanceRefreshPolicy,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
from ui.rotation_generate_tank_role_evidence_support import (
    RotationGenerateTankObligationContext,
)


@dataclass(frozen=True)
class RotationGenerateTankAssignmentEvidence:
    """Exact assignment, strategy, and reviewed defensive evidence for one member/encounter.

    Obligations and strategy remain separate. Assignment and reviewed encounter evidence
    prove what the Tank must do; optional action claims / refresh policy prove how the
    caller has chosen to schedule those responsibilities. No strategy is inferred when
    those fields are empty.

    Concrete taunt-maintenance policies retain exact numeric windows. Reviewed symbolic
    taunt-maintenance policies may end at ``encounter_end`` or an exact reviewed health
    threshold, and may start at a reviewed post-transition resume boundary. They are
    materialized only at Generate time from canonical encounter timing. A symbolic policy
    is never treated as executable before that point.

    Defensive obligations may be supplied directly for explicit audit/test callers, or
    derived from reviewed encounter facts through explicit-clock and/or canonical
    health-threshold timing policies. Direct obligations and reviewed projection inputs
    are mutually exclusive so one mechanic never acquires competing truths.
    """

    encounter_id: str
    member_id: str
    assignments: tuple[ProviderAssignment, ...] = ()
    taunt_policies: tuple[RotationAssignmentTauntPolicy, ...] = ()
    taunt_maintenance_policies: tuple[RotationAssignmentTauntMaintenancePolicy, ...] = ()
    taunt_maintenance_horizon_policies: tuple[
        RotationAssignmentTauntMaintenanceHorizonPolicy, ...
    ] = ()
    taunt_application_claims: tuple[RotationTankTauntActionClaim, ...] = ()
    taunt_maintenance_refresh_policies: tuple[
        RotationTankTauntMaintenanceRefreshPolicy, ...
    ] = ()
    defensive_claims: tuple[RotationTankDefensiveActionClaim, ...] = ()
    defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = ()
    defensive_guide: EncounterBossGuide | None = None
    defensive_facts: tuple[ReconciledEncounterFact, ...] = ()
    defensive_timing_policies: tuple[RotationTankEncounterDefensiveTimingPolicy, ...] = ()
    defensive_threshold_timing_policies: tuple[
        RotationTankEncounterThresholdDefensiveTimingPolicy, ...
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
        object.__setattr__(self, "taunt_maintenance_policies", tuple(self.taunt_maintenance_policies))
        object.__setattr__(
            self,
            "taunt_maintenance_horizon_policies",
            tuple(self.taunt_maintenance_horizon_policies),
        )
        object.__setattr__(self, "taunt_application_claims", tuple(self.taunt_application_claims))
        object.__setattr__(
            self,
            "taunt_maintenance_refresh_policies",
            tuple(self.taunt_maintenance_refresh_policies),
        )
        object.__setattr__(self, "defensive_claims", tuple(self.defensive_claims))
        object.__setattr__(self, "defensive_obligations", tuple(self.defensive_obligations))
        object.__setattr__(self, "defensive_facts", tuple(self.defensive_facts))
        object.__setattr__(self, "defensive_timing_policies", tuple(self.defensive_timing_policies))
        object.__setattr__(
            self,
            "defensive_threshold_timing_policies",
            tuple(self.defensive_threshold_timing_policies),
        )

        has_clock_inputs = bool(self.defensive_guide or self.defensive_timing_policies)
        has_threshold_inputs = bool(self.defensive_threshold_timing_policies)
        has_projection_inputs = bool(has_clock_inputs or has_threshold_inputs or self.defensive_facts)
        if self.defensive_obligations and has_projection_inputs:
            raise ValueError(
                "Tank Generate defensive evidence must use either explicit obligations or reviewed encounter projection, not both"
            )
        if has_clock_inputs:
            if self.defensive_guide is None:
                raise ValueError("Tank Generate reviewed clock defensive evidence requires defensive_guide")
            guide_encounter = str(getattr(self.defensive_guide, "encounter_id", "") or "").strip()
            if guide_encounter.casefold() != encounter_id.casefold():
                raise ValueError(
                    "Tank Generate defensive guide encounter does not match assignment evidence encounter"
                )
            if not self.defensive_timing_policies:
                raise ValueError("Tank Generate reviewed clock defensive evidence requires timing policies")
        if self.defensive_facts and not (
            self.defensive_timing_policies or self.defensive_threshold_timing_policies
        ):
            raise ValueError(
                "Tank Generate reviewed defensive facts require clock or threshold timing policies"
            )


class RotationGenerateTankAssignmentContextSupport:
    """Resolve the selected Tank build/encounter into exact hard obligations and strategy."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        build_adapter: SavedBuildCharacterAdapter | object | None = None,
        bundle_service: RotationTankAssignmentObligationBundleService | object | None = None,
        defensive_bundle_service: RotationTankEncounterDefensiveBundleService | object | None = None,
        threshold_defensive_bundle_service: (
            RotationTankEncounterThresholdDefensiveBundleService | object | None
        ) = None,
        encounter_horizon_service: RotationTankEncounterHorizonService | object | None = None,
        encounter_transition_timing_service: (
            RotationTankEncounterTransitionTimingService | object | None
        ) = None,
        horizon_policy_service: (
            RotationAssignmentTauntMaintenanceHorizonPolicyService | object | None
        ) = None,
    ) -> None:
        self.database_path = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(self.database_path)
        self.bundle_service = bundle_service or RotationTankAssignmentObligationBundleService()
        self.defensive_bundle_service = defensive_bundle_service or RotationTankEncounterDefensiveBundleService()
        self.threshold_defensive_bundle_service = (
            threshold_defensive_bundle_service or RotationTankEncounterThresholdDefensiveBundleService()
        )
        self.encounter_horizon_service = encounter_horizon_service or RotationTankEncounterHorizonService()
        self.encounter_transition_timing_service = (
            encounter_transition_timing_service or RotationTankEncounterTransitionTimingService()
        )
        self.horizon_policy_service = horizon_policy_service or RotationAssignmentTauntMaintenanceHorizonPolicyService()
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
                    "Tank Generate assignment evidence rows must be RotationGenerateTankAssignmentEvidence"
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
            row for row in self._evidence if row.encounter_id.casefold() == encounter_id.casefold()
        )
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                "multiple Tank assignment evidence rows match selected encounter; member identity must be unambiguous"
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
                "cannot derive Tank assignment obligations because saved-build adaptation is unresolved: "
                + detail
            )

        defensive_obligations = self._defensive_obligations(row, evidence_bundle)
        taunt_maintenance_policies = self._taunt_maintenance_policies(row, evidence_bundle)
        bundle = self.bundle_service.compose(
            build=build,
            member_id=row.member_id,
            encounter_id=encounter_id,
            assignments=row.assignments,
            taunt_policies=row.taunt_policies,
            taunt_maintenance_policies=taunt_maintenance_policies,
            defensive_obligations=defensive_obligations,
        )
        return RotationGenerateTankObligationContext(
            encounter_id=bundle.encounter_id,
            taunt_application_requirements=bundle.taunt_application_requirements,
            taunt_maintenance_requirements=bundle.taunt_maintenance_requirements,
            defensive_obligations=bundle.defensive_obligations,
            taunt_application_claims=row.taunt_application_claims,
            taunt_maintenance_policies=row.taunt_maintenance_refresh_policies,
            defensive_claims=row.defensive_claims,
        )

    def _taunt_maintenance_policies(
        self,
        row: RotationGenerateTankAssignmentEvidence,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> tuple[RotationAssignmentTauntMaintenancePolicy, ...]:
        concrete = list(row.taunt_maintenance_policies)
        symbolic = tuple(row.taunt_maintenance_horizon_policies)
        if not symbolic:
            return tuple(concrete)

        thresholds = getattr(evidence_bundle, "health_threshold_projection", None)
        horizon = self.encounter_horizon_service.resolve(
            encounter_id=row.encounter_id,
            health_threshold_projection=thresholds,
        )
        transition_timing = self.encounter_transition_timing_service.project(
            encounter_id=row.encounter_id,
            health_threshold_projection=thresholds,
            horizon=horizon,
        )
        unresolved: list[str] = []
        for policy in symbolic:
            materialized = self.horizon_policy_service.materialize(
                policy=policy,
                horizon=horizon,
                health_threshold_projection=thresholds,
                transition_timing=transition_timing,
            )
            if not getattr(materialized, "resolved", False) or getattr(materialized, "policy", None) is None:
                unresolved.extend(
                    str(item).strip()
                    for item in getattr(materialized, "unresolved", ())
                    if str(item).strip()
                )
                continue
            concrete.append(materialized.policy)

        if unresolved:
            raise ValueError(
                "cannot materialize Tank symbolic taunt-maintenance policy: "
                + "; ".join(dict.fromkeys(unresolved))
            )

        seen: set[str] = set()
        for policy in concrete:
            key = str(policy.requirement_id or "").strip().casefold()
            if key in seen:
                raise ValueError(
                    "Tank Generate taunt-maintenance policy cannot duplicate requirement identity after horizon materialization: "
                    f"{policy.requirement_id}"
                )
            seen.add(key)
        return tuple(concrete)

    def _defensive_obligations(
        self,
        row: RotationGenerateTankAssignmentEvidence,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> tuple[RotationTankDefensiveObligation, ...]:
        if row.defensive_obligations:
            return row.defensive_obligations

        obligations: list[RotationTankDefensiveObligation] = []
        unresolved: list[str] = []

        if row.defensive_timing_policies:
            projection = self.defensive_bundle_service.project(
                guide=row.defensive_guide,
                facts=row.defensive_facts,
                policies=row.defensive_timing_policies,
            )
            unresolved.extend(
                str(item).strip()
                for item in getattr(projection, "unresolved", ())
                if str(item).strip()
            )
            obligations.extend(tuple(getattr(projection, "obligations", ())))

        if row.defensive_threshold_timing_policies:
            thresholds = getattr(evidence_bundle, "health_threshold_projection", None)
            if thresholds is None:
                unresolved.append(
                    "canonical health-threshold projection is unavailable for Tank defensive timing"
                )
            else:
                threshold_encounter = str(getattr(thresholds, "encounter_id", "") or "").strip()
                if threshold_encounter.casefold() != row.encounter_id.casefold():
                    unresolved.append(
                        "canonical health-threshold projection encounter does not match Tank assignment evidence"
                    )
                else:
                    projection = self.threshold_defensive_bundle_service.project(
                        thresholds=thresholds,
                        facts=row.defensive_facts,
                        policies=row.defensive_threshold_timing_policies,
                    )
                    unresolved.extend(
                        str(item).strip()
                        for item in getattr(projection, "unresolved", ())
                        if str(item).strip()
                    )
                    obligations.extend(tuple(getattr(projection, "obligations", ())))

        if unresolved:
            raise ValueError(
                "cannot derive Tank defensive obligations from reviewed encounter evidence: "
                + "; ".join(dict.fromkeys(unresolved))
            )

        if row.defensive_timing_policies or row.defensive_threshold_timing_policies:
            if not obligations:
                raise ValueError(
                    "cannot derive Tank defensive obligations from reviewed encounter evidence: no resolved obligations"
                )

        seen_ids: set[str] = set()
        for obligation in obligations:
            key = str(obligation.obligation_id or "").strip().casefold()
            if key in seen_ids:
                raise ValueError(
                    "duplicate Tank defensive obligation identity after reviewed projection: "
                    f"{obligation.obligation_id}"
                )
            seen_ids.add(key)

        obligations.sort(
            key=lambda item: (
                item.window_start_seconds,
                item.window_end_seconds,
                item.obligation_id,
            )
        )
        return tuple(obligations)


def rotation_generate_tank_assignment_context(
    *,
    page,
    player_build: PlayerBuild,
    evidence_bundle: RotationCanonicalEvidenceBundle,
) -> RotationGenerateTankObligationContext | None:
    support = getattr(page, "_rotation_generate_tank_assignment_context_support", None)
    if support is None:
        support = RotationGenerateTankAssignmentContextSupport()
        page._rotation_generate_tank_assignment_context_support = support
    return support.context_for(player_build, evidence_bundle)


def set_rotation_generate_tank_assignment_evidence(
    page,
    evidence: tuple[RotationGenerateTankAssignmentEvidence, ...],
) -> None:
    support = getattr(page, "_rotation_generate_tank_assignment_context_support", None)
    if support is None:
        support = RotationGenerateTankAssignmentContextSupport()
        page._rotation_generate_tank_assignment_context_support = support
    support.set_evidence(evidence)


__all__ = [
    "RotationGenerateTankAssignmentContextSupport",
    "RotationGenerateTankAssignmentEvidence",
    "rotation_generate_tank_assignment_context",
    "set_rotation_generate_tank_assignment_evidence",
]
