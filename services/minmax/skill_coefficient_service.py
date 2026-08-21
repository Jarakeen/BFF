from __future__ import annotations

from services.eso_database import EsoDatabase
from services.minmax.skill_coefficient import (
    SkillCoefficient,
)


class SkillCoefficientService:
    """
    Loads ESO skill coefficients from the BFF database.
    """

    def __init__(
        self,
        database: EsoDatabase,
    ):
        self.database = database

    def get_for_skill_rank(
        self,
        skill_rank_id: int,
    ) -> tuple[SkillCoefficient, ...]:
        rows = self.database.execute(
            """
            SELECT
                coefficient_number,
                type,
                a,
                b,
                c,
                r,
                avg
            FROM skill_coefficient
            WHERE skill_rank_id = ?
            ORDER BY coefficient_number
            """,
            (skill_rank_id,),
        ).fetchall()

        return tuple(
            SkillCoefficient(
                coefficient_number=int(
                    row["coefficient_number"]
                ),
                type=str(row["type"]),
                a=float(row["a"]),
                b=float(row["b"]),
                c=float(row["c"]),
                r=float(row["r"]),
                avg=(
                    float(row["avg"])
                    if row["avg"] is not None
                    else None
                ),
            )
            for row in rows
        )