from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from services.rotation_dd_periodic_esologs_runtime_evidence_service import (
    RotationDDPeriodicEsoLogsRuntimeEvidenceService,
)
from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


class RotationDDPeriodicEsoLogsSplitDatabaseEvidenceService(
    RotationDDPeriodicEsoLogsRuntimeEvidenceService
):
    """Read DD periodic evidence from a logs DB while resolving identity from canonical ESO data.

    Imported ``log_event`` rows are intentionally kept separate from the canonical
    mechanics database. Canonical skill/rank identity and numeric crosswalk aliases
    come from ``canonical_database_path``; combat-log events come from
    ``logs_database_path``. Both databases are opened read-only by this adapter and
    its base service.
    """

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
        review_service: RotationDDPeriodicRuntimeSemanticsReviewService | None = None,
    ) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        super().__init__(
            logs_database_path,
            coefficient_repository=SkillCoefficientRepository(
                self.canonical_database_path
            ),
            review_service=review_service,
        )

    def _numeric_aliases_for_rank(
        self,
        *,
        skill_id: int,
        morph: int,
        base_ability_id: int,
    ) -> tuple[int, ...]:
        if not self.canonical_database_path.exists():
            raise FileNotFoundError(self.canonical_database_path)
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            aliases = {int(base_ability_id)} if int(base_ability_id) > 0 else set()
            if "skill_rank" in tables:
                aliases.update(
                    int(row["ability_id"])
                    for row in connection.execute(
                        """
                        SELECT ability_id
                        FROM skill_rank
                        WHERE skill_id = ? AND COALESCE(morph, 0) = ?
                          AND ability_id IS NOT NULL
                        """,
                        (int(skill_id), int(morph)),
                    ).fetchall()
                )
            return tuple(sorted(alias for alias in aliases if alias > 0))


__all__ = ["RotationDDPeriodicEsoLogsSplitDatabaseEvidenceService"]
