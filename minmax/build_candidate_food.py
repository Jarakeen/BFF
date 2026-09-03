from __future__ import annotations

import re

from models.build_model import PlayerBuild

from .build_candidate import BuildCandidate, BuildChange
from .provisioning_static_repository import ProvisioningStaticRepository


def enumerate_food_candidates(
    *,
    baseline_build: PlayerBuild,
    character_id: str,
    baseline_build_id: str,
    provisioning_repository: ProvisioningStaticRepository,
    candidate_source: str = "phase12:food",
) -> tuple[BuildCandidate, ...]:
    """Enumerate deterministic one-change food/drink candidates.

    Candidate names come from the canonical provisioning repository. A listed
    food is included only when its static character-sheet effects resolve
    cleanly; dynamic or currently unmapped consumables stay out of the bounded
    Phase 12 search rather than becoming knowingly UNKNOWN candidates.
    """

    current = provisioning_repository.canonical_name(baseline_build.Food)
    candidates: list[BuildCandidate] = []

    for listed_name in provisioning_repository.list_names():
        name = provisioning_repository.canonical_name(listed_name)
        if not name or name.casefold() == current.casefold():
            continue
        effects, unresolved = provisioning_repository.resolve(name)
        if unresolved or not effects:
            continue

        candidate_build = PlayerBuild.from_dict(baseline_build.to_dict())
        candidate_build.Food = name
        candidates.append(
            BuildCandidate.from_build(
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                candidate_id=f"{baseline_build_id}:food:{_candidate_token(name)}",
                candidate_build=candidate_build,
                changes=(
                    BuildChange.from_values(
                        path="Food",
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
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    if not token:
        raise ValueError("Food candidate name cannot produce an empty candidate id.")
    return token
