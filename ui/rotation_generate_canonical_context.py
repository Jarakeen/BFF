from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from minmax.rotation_ability_priority import AbilityPriorityList
from models.build_model import PlayerBuild
from models.effective_build_snapshot import EffectiveBuildSnapshot
from models.raid_plan import RaidPlan, RaidPlanTriggeredResponsibility
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidenceProvider,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodObligation,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _build_character_name(build: PlayerBuild) -> str:
    return _clean(build.Name)


def _build_name(build: PlayerBuild) -> str:
    return _clean(build.BuildName)


class RotationGenerateRoleEvidenceComposer(Protocol):
    def compose(
        self,
        *,
        player_build,
        evidence_bundle,
    ) -> RotationCanonicalRoleEvidence: ...


@dataclass(frozen=True)
class RotationGenerateRoleEvidenceInputs:
    """Authoritative plan evidence plus explicit gameplay-policy context.

    The saved build may supply its persisted role identity and the selected encounter
    may supply its persisted content type. Group-healing reliability and assignment
    exceptions remain explicit because neither fact follows from role or encounter
    identity alone.
    """

    plan_evidence_provider: RotationCandidatePlanEvidenceProvider
    role_output_label: str
    assigned_support_label: str
    reliable_group_healing: bool | None = None
    exception_contexts: tuple[str, ...] = ()
    role_key: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("role_output_label", "assigned_support_label"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        object.__setattr__(
            self,
            "exception_contexts",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.exception_contexts
                    if str(item).strip()
                )
            ),
        )
        if self.role_key is not None:
            object.__setattr__(self, "role_key", str(self.role_key).strip() or None)

    def compose(
        self,
        *,
        player_build,
        content_type: object = "",
    ) -> RotationCanonicalRoleEvidence:
        role_key = str(
            self.role_key
            or getattr(player_build, "Role", "")
            or ""
        ).strip()
        if not role_key:
            raise ValueError(
                "automatic canonical role evidence requires an explicit saved-build role"
            )
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=self.plan_evidence_provider,
            role_output_label=self.role_output_label,
            assigned_support_label=self.assigned_support_label,
            content_type=str(content_type or "").strip(),
            reliable_group_healing=self.reliable_group_healing,
            exception_contexts=self.exception_contexts,
            role_key=role_key,
        )


@dataclass(frozen=True)
class RotationGenerateCanonicalContext:
    """Explicit build/encounter inputs used by the dashboard Generate action.

    Presence of this object opts Generate Rotation into canonical encounter-aware
    orchestration. Absence preserves the legacy/plain generation path. The context
    contains explicit evidence/runtime inputs only; it does not infer them from role,
    class, encounter display names, or UI labels. Optional ``role_evidence`` carries
    already-resolved application facts into the canonical role-aware ranking path.

    ``effective_build`` freezes the exact build configuration used when this context was
    composed. Rotation consumes that snapshot instead of re-resolving Team/Boss/Raid Plan
    state or re-reading a mutable UI selection. Legacy/static test contexts may omit the
    snapshot and continue supplying the page-selected build explicitly at execution time.

    Raid Plan triggered responsibilities remain planning intent. They travel beside the
    exact Raid Plan build snapshot so downstream consumers can resolve runtime conditions,
    but they are never converted here into clock-scheduled Rotation actions.
    """

    evidence_inputs: RotationSelectedEncounterEvidenceInputs
    role_evidence: RotationCanonicalRoleEvidence | None = None
    role_evidence_inputs: RotationGenerateRoleEvidenceInputs | None = None
    role_evidence_composer: RotationGenerateRoleEvidenceComposer | None = None
    cadence_obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...] = ()
    cadence_priorities: AbilityPriorityList | None = None
    cadence_evaluation_context: RotationSupportCadenceEvaluationContext | None = None
    cadence_max_iterations: int = 8
    character_id: str | None = None
    effective_build: EffectiveBuildSnapshot | None = None
    raid_plan_id: str | None = None
    raid_plan_seat_id: str | None = None
    raid_plan_triggered_responsibilities: tuple[
        RaidPlanTriggeredResponsibility, ...
    ] = ()

    def __post_init__(self) -> None:
        role_sources = tuple(
            source
            for source in (
                self.role_evidence,
                self.role_evidence_inputs,
                self.role_evidence_composer,
            )
            if source is not None
        )
        if len(role_sources) > 1:
            raise ValueError(
                "supply only one of role_evidence, role_evidence_inputs, or "
                "role_evidence_composer"
            )
        iterations = int(self.cadence_max_iterations)
        if iterations <= 0:
            raise ValueError("cadence_max_iterations must be positive")
        object.__setattr__(self, "cadence_max_iterations", iterations)
        object.__setattr__(self, "cadence_obligations", tuple(self.cadence_obligations))
        if self.effective_build is not None and not isinstance(
            self.effective_build, EffectiveBuildSnapshot
        ):
            raise TypeError("effective_build must be an EffectiveBuildSnapshot")

        raid_plan_id = _clean(self.raid_plan_id) or None
        raid_plan_seat_id = _clean(self.raid_plan_seat_id) or None
        triggered = tuple(self.raid_plan_triggered_responsibilities)
        object.__setattr__(self, "raid_plan_id", raid_plan_id)
        object.__setattr__(self, "raid_plan_seat_id", raid_plan_seat_id)
        object.__setattr__(self, "raid_plan_triggered_responsibilities", triggered)

        has_raid_plan_context = bool(raid_plan_id or raid_plan_seat_id or triggered)
        if has_raid_plan_context:
            if not raid_plan_id or not raid_plan_seat_id:
                raise ValueError(
                    "Raid Plan Generate context requires both raid_plan_id and raid_plan_seat_id"
                )
            if self.effective_build is None or self.effective_build.source_kind != "raid_plan":
                raise ValueError(
                    "Raid Plan Generate context requires a raid_plan EffectiveBuildSnapshot"
                )
            snapshot_encounter = _clean(self.effective_build.encounter_id).casefold()
            for responsibility in triggered:
                if responsibility.seat_id.casefold() != raid_plan_seat_id.casefold():
                    raise ValueError(
                        "Raid Plan triggered responsibility does not belong to the bound seat"
                    )
                if (
                    snapshot_encounter
                    and responsibility.encounter_id.casefold() != snapshot_encounter
                ):
                    raise ValueError(
                        "Raid Plan triggered responsibility encounter does not match effective build snapshot"
                    )

    def with_raid_plan_member(
        self,
        *,
        raid_plan: RaidPlan,
        seat_id: str,
        build: PlayerBuild,
        encounter_id: str,
        adjustment_labels: tuple[str, ...] = (),
        provenance: tuple[str, ...] = (),
    ) -> "RotationGenerateCanonicalContext":
        """Bind one exact Raid Plan chair and build without inventing execution timing."""
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("raid_plan must be a RaidPlan")
        if not isinstance(build, PlayerBuild):
            raise TypeError("Raid Plan Generate binding requires a PlayerBuild")

        resolved_seat_id = _clean(seat_id)
        resolved_encounter_id = _clean(encounter_id)
        if not resolved_seat_id:
            raise ValueError("Raid Plan Generate binding requires seat_id")
        if not resolved_encounter_id:
            raise ValueError("Raid Plan Generate binding requires encounter_id")

        member = raid_plan.member(resolved_seat_id)
        if member is None:
            raise ValueError(f"Raid Plan has no member for seat_id {resolved_seat_id!r}")

        build_character_name = _build_character_name(build)
        if member.character_name and (
            not build_character_name
            or member.character_name.casefold() != build_character_name.casefold()
        ):
            raise ValueError(
                "Raid Plan member character does not match the supplied effective build"
            )

        build_name = _build_name(build)
        if member.selected_build_name and (
            not build_name
            or member.selected_build_name.casefold() != build_name.casefold()
        ):
            raise ValueError(
                "Raid Plan member selected build does not match the supplied effective build"
            )

        triggered = raid_plan.triggered_for_seat(
            resolved_seat_id,
            encounter_id=resolved_encounter_id,
        )
        snapshot = EffectiveBuildSnapshot.from_raid_plan_build(
            build,
            character_id=member.character_id,
            trial_id=raid_plan.trial_id,
            encounter_id=resolved_encounter_id,
            team_name=raid_plan.team_name,
            adjustment_labels=adjustment_labels,
            provenance=(
                f"Raid Plan {raid_plan.plan_id} seat {member.seat_id}",
                *provenance,
            ),
        )
        return replace(
            self,
            character_id=member.character_id,
            effective_build=snapshot,
            raid_plan_id=raid_plan.plan_id,
            raid_plan_seat_id=member.seat_id,
            raid_plan_triggered_responsibilities=triggered,
        )

    def player_build_for(self, fallback=None):
        """Materialize the exact build this context owns, or use a legacy fallback."""
        if self.effective_build is not None:
            return self.effective_build.materialize()
        return fallback

    def role_evidence_for(
        self,
        *,
        player_build,
        evidence_bundle=None,
        content_type: object = "",
    ) -> RotationCanonicalRoleEvidence | None:
        if self.role_evidence is not None:
            return self.role_evidence
        if self.role_evidence_composer is not None:
            if player_build is None:
                raise ValueError(
                    "select a saved build before composing canonical role evidence"
                )
            if evidence_bundle is None:
                raise ValueError(
                    "automatic canonical role evidence requires a resolved evidence bundle"
                )
            return self.role_evidence_composer.compose(
                player_build=player_build,
                evidence_bundle=evidence_bundle,
            )
        if self.role_evidence_inputs is None:
            return None
        return self.role_evidence_inputs.compose(
            player_build=player_build,
            content_type=content_type,
        )


__all__ = [
    "RotationGenerateCanonicalContext",
    "RotationGenerateRoleEvidenceComposer",
    "RotationGenerateRoleEvidenceInputs",
]
