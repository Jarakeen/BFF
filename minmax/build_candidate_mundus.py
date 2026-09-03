from __future__ import annotations

import re

from models.build_model import PlayerBuild

from .build_candidate import BuildCandidate, BuildChange
from .mundus_repository import MundusRepository


def enumerate_mundus_candidates(
    *,
    baseline_build: PlayerBuild,
    character_id: str,
    baseline_build_id: str,
    mundus_repository: MundusRepository,
    candidate_source: str = "phase12:mundus",
) -> tuple[BuildCandidate, ...]:
    """Enumerate one-change Mundus candidates from canonical repository names.

    The baseline is serialized for each candidate and never mutated.  Candidate
    enumeration does not score or assume that a stone is beneficial; unsupported
    effects remain the responsibility of the existing context/evaluation stack.
    """

    current = str(baseline_build.Mundus or "").strip()
    candidates: list[BuildCandidate] = []

    for mundus_name in mundus_repository.list_names():
        name = str(mundus_name or "").strip()
        if not name or name == current:
            continue

        candidate_build = PlayerBuild.from_dict(baseline_build.to_dict())
        candidate_build.Mundus = name
        candidates.append(
            BuildCandidate.from_build(
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                candidate_id=f"{baseline_build_id}:mundus:{_candidate_token(name)}",
                candidate_build=candidate_build,
                changes=(
                    BuildChange.from_values(
                        path="Mundus",
                        before=current,
                        after=name,
                        source=candidate_source,
                    ),
                ),
                candidate_source=candidate_source,
            )
        )

    return tuple(candidates)


def _candidate_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not token:
        raise ValueError("Mundus candidate name cannot produce an empty candidate id.")
    return token
