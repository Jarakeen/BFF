from __future__ import annotations

from pathlib import Path

from services.rotation_dd_reviewed_skill_component_repository import (
    RotationDDReviewedSkillComponentRepository,
)


class RotationReviewedSkillComponentRepository(
    RotationDDReviewedSkillComponentRepository
):
    """Canonical reviewed component identity overlay used by rotation mechanics.

    The underlying reviewed rows were first captured while closing DD coverage gaps,
    but their contents are mechanic identity facts rather than DD-only policy. This
    compatibility adapter gives shared timing/runtime consumers a role-neutral name
    while preserving the existing reviewed source and DD imports.
    """

    def __init__(self, database_path: str | Path, **kwargs) -> None:
        super().__init__(database_path, **kwargs)


__all__ = ["RotationReviewedSkillComponentRepository"]
