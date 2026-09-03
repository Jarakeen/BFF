from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any

from models.build_model import PlayerBuild


class CandidateEvaluationState(str, Enum):
    """Whether a proposed build may enter authoritative candidate evaluation."""

    EVALUABLE = "evaluable"
    UNKNOWN = "unknown"
    INVALID = "invalid"


@dataclass(frozen=True)
class BuildChange:
    """One explicit change between the authoritative baseline and a candidate."""

    path: str
    before_json: str
    after_json: str
    source: str

    @classmethod
    def from_values(
        cls,
        *,
        path: str,
        before: Any,
        after: Any,
        source: str,
    ) -> "BuildChange":
        normalized_path = str(path or "").strip()
        normalized_source = str(source or "").strip()
        if not normalized_path:
            raise ValueError("Build change path is required.")
        if not normalized_source:
            raise ValueError("Build change source is required.")
        return cls(
            path=normalized_path,
            before_json=_canonical_json(before),
            after_json=_canonical_json(after),
            source=normalized_source,
        )

    @property
    def before(self) -> Any:
        return json.loads(self.before_json)

    @property
    def after(self) -> Any:
        return json.loads(self.after_json)


@dataclass(frozen=True)
class BuildCandidate:
    """Immutable Phase 12 snapshot of a proposed canonical build.

    The authoritative saved build is never held by mutable reference.  The
    candidate stores a canonical serialized snapshot and reconstructs a fresh
    ``PlayerBuild`` for downstream evaluation on demand.
    """

    character_id: str
    baseline_build_id: str
    candidate_id: str
    candidate_build_json: str
    changes: tuple[BuildChange, ...]
    candidate_source: str
    evaluation_state: CandidateEvaluationState = CandidateEvaluationState.EVALUABLE
    unresolved: tuple[str, ...] = ()

    @classmethod
    def from_build(
        cls,
        *,
        character_id: str,
        baseline_build_id: str,
        candidate_id: str,
        candidate_build: PlayerBuild,
        changes: tuple[BuildChange, ...],
        candidate_source: str,
        evaluation_state: CandidateEvaluationState = CandidateEvaluationState.EVALUABLE,
        unresolved: tuple[str, ...] = (),
    ) -> "BuildCandidate":
        identifiers = {
            "character_id": str(character_id or "").strip(),
            "baseline_build_id": str(baseline_build_id or "").strip(),
            "candidate_id": str(candidate_id or "").strip(),
            "candidate_source": str(candidate_source or "").strip(),
        }
        missing = [name for name, value in identifiers.items() if not value]
        if missing:
            raise ValueError(f"Build candidate requires: {', '.join(missing)}.")

        normalized_unresolved = tuple(
            item
            for item in (str(value or "").strip() for value in unresolved)
            if item
        )
        if evaluation_state is CandidateEvaluationState.EVALUABLE and normalized_unresolved:
            raise ValueError(
                "An evaluable build candidate cannot carry unresolved evidence."
            )

        return cls(
            character_id=identifiers["character_id"],
            baseline_build_id=identifiers["baseline_build_id"],
            candidate_id=identifiers["candidate_id"],
            candidate_build_json=_canonical_json(candidate_build.to_dict()),
            changes=tuple(changes),
            candidate_source=identifiers["candidate_source"],
            evaluation_state=evaluation_state,
            unresolved=normalized_unresolved,
        )

    @property
    def candidate_build(self) -> PlayerBuild:
        """Return a fresh mutable build copy for the existing evaluation stack."""

        return PlayerBuild.from_dict(json.loads(self.candidate_build_json))

    @property
    def is_evaluable(self) -> bool:
        return self.evaluation_state is CandidateEvaluationState.EVALUABLE


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
