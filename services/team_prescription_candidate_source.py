from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from typing import Any

from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild

from .team_prescription import PrescribedRoster
from .team_role_autofill import normalize_team_role, slot_role_family
from .team_prescription_slot_constraints import PrescribedSlotBuildConstraint


@dataclass(frozen=True)
class PrescribedOpenSlotCandidate:
    """Immutable build template for an open roster chair.

    This is deliberately not a Phase 12 ``BuildCandidate``. An open chair has no
    authoritative baseline build, so representing it as a baseline mutation would
    manufacture comparison evidence that does not exist.

    ``player_name`` is optional because open-slot candidates may be either reusable
    build templates or real saved-player builds. When present, downstream roster
    optimization must treat that player as consumable exactly once.

    ``candidate_metadata_json`` carries provenance and partial observations that do
    not belong in a canonical ``PlayerBuild``. This is how an ESO Logs observation
    can honestly say "these sets/skills were observed" without fabricating gear-slot
    placement, traits, CP, food, or any other unobserved build field.
    """

    candidate_id: str
    candidate_build_json: str
    candidate_source: str
    player_name: str | None = None
    candidate_metadata_json: str = "{}"

    @classmethod
    def from_build(
        cls,
        *,
        candidate_id: str,
        candidate_build: PlayerBuild,
        candidate_source: str,
        player_name: str | None = None,
        candidate_metadata: dict[str, Any] | None = None,
    ) -> "PrescribedOpenSlotCandidate":
        normalized_id = str(candidate_id or "").strip()
        normalized_source = str(candidate_source or "").strip()
        normalized_player = str(player_name or "").strip() or None
        if not normalized_id:
            raise ValueError("open-slot candidate_id is required")
        if not normalized_source:
            raise ValueError("open-slot candidate_source is required")
        metadata = candidate_metadata or {}
        if not isinstance(metadata, dict):
            raise ValueError("open-slot candidate metadata must be a JSON object")
        return cls(
            candidate_id=normalized_id,
            candidate_build_json=json.dumps(
                candidate_build.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            candidate_source=normalized_source,
            player_name=normalized_player,
            candidate_metadata_json=json.dumps(
                metadata,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )

    @property
    def candidate_build(self) -> PlayerBuild:
        return PlayerBuild.from_dict(json.loads(self.candidate_build_json))

    @property
    def candidate_metadata(self) -> dict[str, Any]:
        try:
            value = json.loads(self.candidate_metadata_json or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"candidate {self.candidate_id!r} contains invalid metadata JSON"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"candidate {self.candidate_id!r} metadata must be a JSON object"
            )
        return value

    @property
    def has_complete_build_snapshot(self) -> bool:
        return bool(self.candidate_metadata.get("complete_build", True))


@dataclass(frozen=True)
class PrescribedObjectiveMeasurement:
    """Absolute, canonical objective evidence for one open-slot build template."""

    objective: EvaluationObjective
    value: float | None
    metric_name: str
    constraints: tuple[CandidateConstraint, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    rejection_reason: str | None = None

    def __post_init__(self) -> None:
        metric_name = str(self.metric_name or "").strip()
        if not metric_name:
            raise ValueError("open-slot objective metric_name is required")
        if self.value is not None and float(self.value) < 0:
            raise ValueError("open-slot objective value cannot be negative")
        object.__setattr__(self, "metric_name", metric_name)
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(item).strip() for item in self.unresolved if str(item).strip()),
        )

    @property
    def blocking_constraints(self) -> tuple[CandidateConstraint, ...]:
        return tuple(
            constraint
            for constraint in self.constraints
            if constraint.status
            in (
                ConstraintStatus.WORSENED,
                ConstraintStatus.UNSATISFIED,
                ConstraintStatus.UNKNOWN,
            )
        )

    @property
    def is_rankable(self) -> bool:
        return (
            self.value is not None
            and not self.blocking_constraints
            and not self.unresolved
            and not self.rejection_reason
        )


@dataclass(frozen=True)
class PrescribedOpenSlotCandidateEvidence:
    candidate: PrescribedOpenSlotCandidate
    measurement: PrescribedObjectiveMeasurement
    provider_requirement_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        provider_ids = tuple(
            dict.fromkeys(
                value
                for value in (
                    str(item or "").strip() for item in self.provider_requirement_ids
                )
                if value
            )
        )
        object.__setattr__(self, "provider_requirement_ids", provider_ids)


OpenSlotObjectiveEvaluator = Callable[
    [PrescribedOpenSlotCandidate, str], PrescribedObjectiveMeasurement
]
OpenSlotProviderResolver = Callable[
    [PrescribedOpenSlotCandidate, str], tuple[str, ...]
]


@dataclass(frozen=True)
class PrescribedCandidateSourceResult:
    evidence_by_slot: dict[str, tuple[PrescribedOpenSlotCandidateEvidence, ...]]
    unresolved: tuple[str, ...] = ()


def evaluate_open_slot_candidate_source(
    *,
    roster: PrescribedRoster,
    candidates: tuple[PrescribedOpenSlotCandidate, ...],
    evaluate_objective: OpenSlotObjectiveEvaluator,
    resolve_provider_requirements: OpenSlotProviderResolver | None = None,
    build_constraints_by_slot: dict[str, PrescribedSlotBuildConstraint] | None = None,
) -> PrescribedCandidateSourceResult:
    """Evaluate real build templates for every compatible open roster slot.

    The supplied evaluator must use an existing canonical role-specific engine. This
    service owns only source orchestration, role boundaries, immutable snapshots, and
    explicit failure reporting. It never invents a baseline, objective value, player,
    provider assignment, or unsupported ESO mechanic.
    """

    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("open-slot candidate source contains duplicate candidate_id values")

    build_constraints_by_slot = build_constraints_by_slot or {}
    normalized_build_constraints = {
        str(slot_name).strip().casefold(): constraint
        for slot_name, constraint in build_constraints_by_slot.items()
        if str(slot_name).strip()
    }
    by_slot: dict[str, tuple[PrescribedOpenSlotCandidateEvidence, ...]] = {}
    unresolved: list[str] = []

    anchored_players = {
        assignment.player_name.casefold()
        for assignment in roster.assignments
        if assignment.player_name
    }

    for assignment in roster.assignments:
        if assignment.player_name is not None:
            continue
        required_role = slot_role_family(assignment.slot_name)
        build_constraint = normalized_build_constraints.get(
            assignment.slot_name.casefold()
        )
        compatible = tuple(
            candidate
            for candidate in candidates
            if normalize_team_role(candidate.candidate_build.Role) == required_role
            and (
                build_constraint is None
                or build_constraint.matches_candidate(
                    candidate.candidate_build,
                    candidate.candidate_metadata,
                )
            )
            and not (
                candidate.player_name
                and candidate.player_name.casefold() in anchored_players
            )
        )
        rows: list[PrescribedOpenSlotCandidateEvidence] = []
        for candidate in compatible:
            try:
                measurement = evaluate_objective(candidate, assignment.slot_name)
                provider_ids = (
                    resolve_provider_requirements(candidate, assignment.slot_name)
                    if resolve_provider_requirements is not None
                    else ()
                )
            except Exception as exc:
                unresolved.append(
                    f"{assignment.slot_name}: candidate {candidate.candidate_id!r} "
                    f"could not be evaluated: {exc}"
                )
                continue
            rows.append(
                PrescribedOpenSlotCandidateEvidence(
                    candidate=candidate,
                    measurement=measurement,
                    provider_requirement_ids=provider_ids,
                )
            )
        by_slot[assignment.slot_name] = tuple(rows)
        if not compatible:
            if build_constraint is None:
                unresolved.append(
                    f"{assignment.slot_name}: no role-compatible open-slot build template is available"
                )
            else:
                unresolved.append(
                    f"{assignment.slot_name}: no role-compatible open-slot build template "
                    f"satisfies required ingredients {build_constraint.summary}"
                )
        elif not rows:
            unresolved.append(
                f"{assignment.slot_name}: no role-compatible build template produced "
                "objective evidence"
            )

    return PrescribedCandidateSourceResult(
        evidence_by_slot=by_slot,
        unresolved=tuple(dict.fromkeys(unresolved)),
    )
