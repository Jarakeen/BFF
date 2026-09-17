from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeUnresolvedIncumbentAdmission:
    admissible: bool
    introduced: tuple[str, ...]
    inherited: tuple[str, ...]
    removed: tuple[str, ...]


class ExtremeUnresolvedIncumbentAdmissionService:
    """Protect proof quality while a staged Extreme optimizer changes incumbents.

    A candidate may keep unresolved blockers already carried by the incumbent or
    remove them. It may not introduce a different/new blocker merely because its
    numeric objective score is higher. Exact blocker strings are intentionally the
    identity contract here; normalization would risk merging mechanically distinct
    proof gaps that only happen to sound similar.
    """

    @staticmethod
    def review(
        current_unresolved: tuple[str, ...],
        candidate_unresolved: tuple[str, ...],
    ) -> ExtremeUnresolvedIncumbentAdmission:
        current = tuple(dict.fromkeys(item for item in current_unresolved if item))
        candidate = tuple(dict.fromkeys(item for item in candidate_unresolved if item))
        current_set = set(current)
        candidate_set = set(candidate)
        introduced = tuple(item for item in candidate if item not in current_set)
        inherited = tuple(item for item in candidate if item in current_set)
        removed = tuple(item for item in current if item not in candidate_set)
        return ExtremeUnresolvedIncumbentAdmission(
            admissible=not introduced,
            introduced=introduced,
            inherited=inherited,
            removed=removed,
        )


__all__ = [
    "ExtremeUnresolvedIncumbentAdmission",
    "ExtremeUnresolvedIncumbentAdmissionService",
]
