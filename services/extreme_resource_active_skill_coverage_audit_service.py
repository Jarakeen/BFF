from __future__ import annotations

"""Audit every canonical active skill/morph for Extreme max-resource relevance.

The existing resource active-bar service proves the legal witness bars required by
reviewed *passives*.  That is narrower than proving the complete active-skill axis:
an active skill or morph may itself change a maximum resource or create a state
that changes it.

This service owns no ESO stat math.  It inventories the canonical active-skill
universe and conservatively classifies each max-rank description for one reviewed
max-resource objective.  Descriptions that cannot modify the target maximum
resource are safely pruned.  Direct resource mutations and named resource hazards
remain explicit relevant debt until an executable mechanic owns them.  Missing
canonical description evidence fails closed.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_gear_set_resource_objective_screening_service import (
    ExtremeGearSetResourceObjectiveScreeningService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillUniverseService,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class ExtremeResourceActiveSkillCoverageAudit:
    objective_key: str
    active_skills_reviewed: int
    proven_irrelevant: tuple[str, ...]
    relevant: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def denominator_proven(self) -> bool:
        classified = (
            len(self.proven_irrelevant)
            + len(self.relevant)
            + len(self.unresolved)
        )
        return self.active_skills_reviewed > 0 and classified == self.active_skills_reviewed

    @property
    def projection_complete(self) -> bool:
        """Whether the active-skill axis can be closed for this objective."""
        return self.denominator_proven and not self.relevant and not self.unresolved


class ExtremeResourceActiveSkillCoverageAuditService:
    """Classify every canonical player active/morph for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        universe_service: ExtremeSkillUniverseService | None = None,
    ) -> None:
        if universe_service is None and database_path is None:
            raise ValueError("database_path is required when no skill universe service is supplied")
        self.universe_service = universe_service or ExtremeSkillUniverseService(database_path)  # type: ignore[arg-type]

    @staticmethod
    def _identity(row: ExtremePlayerSkillRecord) -> str:
        line = str(row.skill_line or "").strip() or "<no line>"
        name = str(row.name or "").strip() or f"skill:{row.skill_id}"
        return f"[{row.domain.value}] {line} :: {name}"

    def build(self, objective_key: str) -> ExtremeResourceActiveSkillCoverageAudit:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource active-skill objective: {objective_key!r}")

        actives = tuple(self.universe_service.actives())
        irrelevant: list[str] = []
        relevant: list[str] = []
        unresolved: list[str] = []

        for row in actives:
            identity = self._identity(row)
            description = " ".join(str(row.description or "").split())

            # A canonical active without a concrete max-rank description cannot be
            # proven irrelevant from prose.  Known non-combat non-crafted lines are
            # structural utility and may be safely excluded from combat stat search.
            if not description:
                if row.known_noncombat_line and not row.is_crafted:
                    irrelevant.append(identity)
                else:
                    unresolved.append(f"{identity}: missing canonical max-rank description")
                continue

            screening = ExtremeGearSetResourceObjectiveScreeningService.review(
                description,
                key,
            )
            if screening.proven_irrelevant:
                irrelevant.append(identity)
                continue

            detail = "; ".join(screening.blockers) or "resource-relevant active mechanic"
            relevant.append(f"{identity}: {detail}")

        return ExtremeResourceActiveSkillCoverageAudit(
            objective_key=key,
            active_skills_reviewed=len(actives),
            proven_irrelevant=tuple(irrelevant),
            relevant=tuple(relevant),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeResourceActiveSkillCoverageAudit",
    "ExtremeResourceActiveSkillCoverageAuditService",
]
