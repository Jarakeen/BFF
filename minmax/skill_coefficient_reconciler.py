from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DATABASE = Path("data/eso.db")
DEFAULT_COEFFICIENT_FILE = Path(
    "data/raw/skill_coef_raw.json"
)


class SkillCoefficientReconciler:
    """
    Rebuild skill_coefficient against the current skill_rank table.

    The raw coefficient source identifies abilities by ESO ability ID.
    The live database identifies skill ranks internally by skill_rank.id.

    This reconciler bridges those two identifiers without rebuilding
    skill or skill_rank.
    """

    def __init__(
        self,
        database: Path = DEFAULT_DATABASE,
        coefficient_file: Path = DEFAULT_COEFFICIENT_FILE,
    ):
        self.database_path = Path(database)
        self.coefficient_file = Path(coefficient_file)

    def run(self) -> dict[str, int]:
        """
        Rebuild skill_coefficient and return reconciliation statistics.
        """

        raw_records = self._load_raw_records()

        connection = sqlite3.connect(
            self.database_path
        )

        try:
            connection.execute("PRAGMA foreign_keys = ON")

            rank_map = self._load_rank_map(
                connection
            )

            matched_records = []
            unmatched_raw = 0

            for record in raw_records:

                ability_id = self._ability_id(
                    record
                )

                if ability_id is None:
                    continue

                skill_rank_id = rank_map.get(
                    ability_id
                )

                if skill_rank_id is None:
                    unmatched_raw += 1
                    continue

                matched_records.append(
                    (
                        skill_rank_id,
                        record,
                    )
                )

            coefficient_rows = []

            for skill_rank_id, record in matched_records:

                coefficient_rows.extend(
                    self._coefficient_rows(
                        skill_rank_id,
                        record,
                    )
                )

            self._validate_reconciliation(
                connection,
                rank_map,
                raw_records,
                matched_records,
                coefficient_rows,
            )

            connection.execute(
                "BEGIN"
            )

            connection.execute(
                "DELETE FROM skill_coefficient"
            )

            connection.executemany(
                """
                INSERT INTO skill_coefficient (
                    skill_rank_id,
                    coefficient_number,
                    type,
                    a,
                    b,
                    c,
                    r,
                    avg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                coefficient_rows,
            )

            connection.commit()

            orphaned_rows = connection.execute(
                """
                SELECT COUNT(*)
                FROM skill_coefficient sc
                LEFT JOIN skill_rank sr
                    ON sr.id = sc.skill_rank_id
                WHERE sr.id IS NULL
                """
            ).fetchone()[0]

            matched_ability_ids = len(
                matched_records
            )

            return {
                "raw_records": len(raw_records),
                "current_skill_ranks": len(
                    rank_map
                ),
                "matched_abilities": (
                    matched_ability_ids
                ),
                "unmatched_raw": unmatched_raw,
                "coefficient_rows": len(
                    coefficient_rows
                ),
                "orphaned_rows": orphaned_rows,
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def _load_raw_records(
        self,
    ) -> list[dict[str, Any]]:

        if not self.coefficient_file.exists():
            raise FileNotFoundError(
                f"Coefficient file not found: "
                f"{self.coefficient_file}"
            )

        with self.coefficient_file.open(
            "r",
            encoding="utf-8",
        ) as handle:

            payload = json.load(handle)

        if not isinstance(payload, dict):
            raise ValueError(
                "Coefficient source must be a JSON object."
            )

        records = payload.get(
            "skillCoef"
        )

        if not isinstance(records, list):
            raise ValueError(
                "Coefficient source does not contain "
                "a skillCoef list."
            )

        return records

    def _load_rank_map(
        self,
        connection: sqlite3.Connection,
    ) -> dict[int, int]:

        rows = connection.execute(
            """
            SELECT id, ability_id
            FROM skill_rank
            """
        ).fetchall()

        rank_map: dict[int, int] = {}

        for skill_rank_id, ability_id in rows:

            if ability_id is None:
                continue

            rank_map[int(ability_id)] = int(
                skill_rank_id
            )

        return rank_map

    def _ability_id(
        self,
        record: dict[str, Any],
    ) -> int | None:

        value = record.get("id")

        if value is None:
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    def _coefficient_rows(
        self,
        skill_rank_id: int,
        record: dict[str, Any],
    ) -> list[tuple]:

        rows = []

        for number in range(1, 7):

            type_value = self._text(
                record.get(
                    f"type{number}"
                )
            )

            a = self._number(
                record.get(
                    f"a{number}"
                )
            )

            b = self._number(
                record.get(
                    f"b{number}"
                )
            )

            c = self._number(
                record.get(
                    f"c{number}"
                )
            )

            r = self._number(
                record.get(
                    f"R{number}"
                )
            )

            avg = self._number(
                record.get(
                    f"avg{number}"
                )
            )

            if self._is_empty_slot(
                type_value,
                a,
                b,
                c,
                r,
                avg,
            ):
                continue

            rows.append(
                (
                    skill_rank_id,
                    number,
                    type_value,
                    a,
                    b,
                    c,
                    r,
                    avg,
                )
            )

        return rows

    @staticmethod
    def _is_empty_slot(
        type_value: str | None,
        a: float | None,
        b: float | None,
        c: float | None,
        r: float | None,
        avg: float | None,
    ) -> bool:

        return (
            type_value is None
            and a is None
            and b is None
            and c is None
            and r is None
            and avg is None
        )

    @staticmethod
    def _text(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        text = str(value).strip()

        if not text:
            return None

        return text

    @staticmethod
    def _number(
        value: Any,
    ) -> float | None:

        if value is None:
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    def _validate_reconciliation(
        self,
        connection: sqlite3.Connection,
        rank_map: dict[int, int],
        raw_records: list[dict[str, Any]],
        matched_records: list[
            tuple[int, dict[str, Any]]
        ],
        coefficient_rows: list[tuple],
    ) -> None:

        if not rank_map:
            raise ValueError(
                "skill_rank contains no usable ability IDs."
            )

        if not raw_records:
            raise ValueError(
                "Coefficient source contains no records."
            )

        if not matched_records:
            raise ValueError(
                "No coefficient records matched "
                "the current skill_rank table."
            )

        if not coefficient_rows:
            raise ValueError(
                "Matched coefficient records produced "
                "no coefficient rows."
            )

        missing_orphans = connection.execute(
            """
            SELECT COUNT(*)
            FROM skill_rank
            """
        ).fetchone()[0]

        if missing_orphans <= 0:
            raise ValueError(
                "Current skill_rank table is empty."
            )


def reconcile_skill_coefficients(
    database: Path = DEFAULT_DATABASE,
    coefficient_file: Path = DEFAULT_COEFFICIENT_FILE,
) -> dict[str, int]:
    """
    Convenience wrapper for rebuilding skill coefficients.
    """

    return SkillCoefficientReconciler(
        database=database,
        coefficient_file=coefficient_file,
    ).run()


if __name__ == "__main__":

    result = reconcile_skill_coefficients()

    print(
        "Skill coefficient reconciliation complete."
    )

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )
        