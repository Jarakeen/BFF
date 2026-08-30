from __future__ import annotations

import argparse
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "eso.db"

_PLACEHOLDER_RE = re.compile(r"\$(\d+)|<<\s*(\d+)\s*>>")


@dataclass(frozen=True)
class CoefficientSlotAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    name: str
    coefficient_type: str
    a: float
    b: float
    c: float
    r: float
    avg: float | None
    raw_slot_type: str | None
    raw_slot_a: float | None
    raw_slot_b: float | None
    raw_slot_c: float | None
    raw_slot_r: float | None
    raw_slot_avg: float | None
    raw_coef: str | None
    coef_types: str | None
    coef_description: str | None
    raw_description: str | None
    raw_tooltip: str | None

    @property
    def placeholder_numbers(self) -> tuple[int, ...]:
        values: set[int] = set()
        for text in (self.coef_description, self.raw_description, self.raw_tooltip):
            for match in _PLACEHOLDER_RE.finditer(str(text or "")):
                value = match.group(1) or match.group(2)
                if value:
                    values.add(int(value))
        return tuple(sorted(values))

    @property
    def slot_placeholder_is_present(self) -> bool:
        return self.coefficient_number in self.placeholder_numbers

    @property
    def has_raw_slot(self) -> bool:
        return any(
            value is not None
            for value in (
                self.raw_slot_type,
                self.raw_slot_a,
                self.raw_slot_b,
                self.raw_slot_c,
                self.raw_slot_r,
                self.raw_slot_avg,
            )
        )

    @property
    def raw_slot_matches_coefficient(self) -> bool | None:
        if not self.has_raw_slot:
            return None
        if self.raw_slot_type is not None and str(self.raw_slot_type) != str(self.coefficient_type):
            return False
        comparisons = (
            (self.raw_slot_a, self.a),
            (self.raw_slot_b, self.b),
            (self.raw_slot_c, self.c),
            (self.raw_slot_r, self.r),
            (self.raw_slot_avg, self.avg),
        )
        for raw_value, normalized_value in comparisons:
            if raw_value is None and normalized_value is None:
                continue
            if raw_value is None or normalized_value is None:
                return False
            if not math.isclose(float(raw_value), float(normalized_value), rel_tol=1e-9, abs_tol=1e-9):
                return False
        return True


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _optional_expr(columns: set[str], alias: str, column: str) -> str:
    return f"{alias}.{column}" if column in columns else "NULL"


def load_slot_audit(
    database_path: str | Path,
    *,
    skill_rank_id: int | None = None,
    ability_id: int | None = None,
    limit: int | None = None,
) -> tuple[CoefficientSlotAuditRow, ...]:
    """Read coefficient-slot and tooltip-placeholder evidence without inferring mechanics."""

    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        required = {"skill_rank", "skill_coefficient", "ability"}
        missing = sorted(name for name in required if not _table_exists(db, name))
        if missing:
            raise RuntimeError("Required tables are missing: " + ", ".join(missing))

        sr_columns = _columns(db, "skill_rank")
        a_columns = _columns(db, "ability")

        where: list[str] = []
        params: list[object] = []
        if skill_rank_id is not None:
            where.append("sr.id = ?")
            params.append(int(skill_rank_id))
        if ability_id is not None:
            where.append("sr.ability_id = ?")
            params.append(int(ability_id))

        raw_slot_columns: list[str] = []
        for number in range(1, 7):
            for field in ("type", "a", "b", "c", "r", "avg"):
                column = f"{field}{number}" if field != "r" else f"r{number}"
                raw_slot_columns.append(
                    f"{_optional_expr(a_columns, 'a', column)} AS raw_{field}{number}"
                )

        sql = f"""
            SELECT
                sr.id AS skill_rank_id,
                sc.coefficient_number,
                sr.ability_id,
                COALESCE(NULLIF(a.name, ''), NULLIF({_optional_expr(sr_columns, 'sr', 'raw_name')}, ''), '') AS name,
                sc.type AS coefficient_type,
                sc.a,
                sc.b,
                sc.c,
                sc.r,
                sc.avg,
                {_optional_expr(sr_columns, 'sr', 'raw_coef')} AS raw_coef,
                {_optional_expr(sr_columns, 'sr', 'coef_types')} AS coef_types,
                {_optional_expr(a_columns, 'a', 'coef_description')} AS coef_description,
                COALESCE({_optional_expr(sr_columns, 'sr', 'raw_description')}, {_optional_expr(a_columns, 'a', 'raw_description')}) AS raw_description,
                COALESCE({_optional_expr(sr_columns, 'sr', 'raw_tooltip')}, {_optional_expr(a_columns, 'a', 'raw_tooltip')}) AS raw_tooltip,
                {', '.join(raw_slot_columns)}
            FROM skill_rank sr
            JOIN skill_coefficient sc ON sc.skill_rank_id = sr.id
            LEFT JOIN ability a ON a.ability_id = sr.ability_id
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sr.id, sc.coefficient_number"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, int(limit)))

        rows = db.execute(sql, tuple(params)).fetchall()

    results: list[CoefficientSlotAuditRow] = []
    for row in rows:
        number = int(row["coefficient_number"])
        raw_prefixes = {
            field: row[f"raw_{field}{number}"] if 1 <= number <= 6 else None
            for field in ("type", "a", "b", "c", "r", "avg")
        }
        results.append(
            CoefficientSlotAuditRow(
                skill_rank_id=int(row["skill_rank_id"]),
                coefficient_number=number,
                ability_id=int(row["ability_id"]),
                name=str(row["name"] or ""),
                coefficient_type=str(row["coefficient_type"] or ""),
                a=float(row["a"] or 0.0),
                b=float(row["b"] or 0.0),
                c=float(row["c"] or 0.0),
                r=float(row["r"] if row["r"] is not None else 1.0),
                avg=float(row["avg"]) if row["avg"] is not None else None,
                raw_slot_type=str(raw_prefixes["type"]) if raw_prefixes["type"] is not None else None,
                raw_slot_a=float(raw_prefixes["a"]) if raw_prefixes["a"] is not None else None,
                raw_slot_b=float(raw_prefixes["b"]) if raw_prefixes["b"] is not None else None,
                raw_slot_c=float(raw_prefixes["c"]) if raw_prefixes["c"] is not None else None,
                raw_slot_r=float(raw_prefixes["r"]) if raw_prefixes["r"] is not None else None,
                raw_slot_avg=float(raw_prefixes["avg"]) if raw_prefixes["avg"] is not None else None,
                raw_coef=row["raw_coef"],
                coef_types=row["coef_types"],
                coef_description=row["coef_description"],
                raw_description=row["raw_description"],
                raw_tooltip=row["raw_tooltip"],
            )
        )
    return tuple(results)


def summarize(rows: tuple[CoefficientSlotAuditRow, ...]) -> dict[str, int]:
    matches = [row.raw_slot_matches_coefficient for row in rows]
    return {
        "components": len(rows),
        "raw_slot_present": sum(row.has_raw_slot for row in rows),
        "raw_slot_match": sum(value is True for value in matches),
        "raw_slot_mismatch": sum(value is False for value in matches),
        "slot_placeholder_present": sum(row.slot_placeholder_is_present for row in rows),
        "any_placeholder": sum(bool(row.placeholder_numbers) for row in rows),
    }


def _clean(value: object, *, max_len: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit raw coefficient slots against normalized rows and tooltip placeholders."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--skill-rank-id", type=int)
    parser.add_argument("--ability-id", type=int)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    rows = load_slot_audit(
        args.database,
        skill_rank_id=args.skill_rank_id,
        ability_id=args.ability_id,
        limit=args.limit,
    )
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 3 COEFFICIENT SLOT SEMANTICS AUDIT")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Components:            {counts['components']}")
    print(f"Raw source slot:       {counts['raw_slot_present']}")
    print(f"Raw slot matches:      {counts['raw_slot_match']}")
    print(f"Raw slot mismatches:   {counts['raw_slot_mismatch']}")
    print(f"Any placeholders:      {counts['any_placeholder']}")
    print(f"Own slot placeholder:  {counts['slot_placeholder_present']}")
    print()
    print("NOTE: matching slot numbers are evidence of source alignment, not yet a mechanic classification.")
    print("This tool does not write skill_component_classification or infer damage/heal/DoT/AoE semantics.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(
            "normalized: "
            f"type={row.coefficient_type} a={row.a} b={row.b} c={row.c} r={row.r} avg={row.avg}"
        )
        print(
            "raw slot:   "
            f"type={row.raw_slot_type} a={row.raw_slot_a} b={row.raw_slot_b} "
            f"c={row.raw_slot_c} r={row.raw_slot_r} avg={row.raw_slot_avg} "
            f"match={row.raw_slot_matches_coefficient}"
        )
        print(
            f"placeholders={row.placeholder_numbers} "
            f"contains_own_slot={row.slot_placeholder_is_present}"
        )
        if row.coef_types:
            print(f"coef_types:       {_clean(row.coef_types)}")
        if row.raw_coef:
            print(f"raw_coef:         {_clean(row.raw_coef)}")
        if row.coef_description:
            print(f"coef_description: {_clean(row.coef_description)}")
        if row.raw_description:
            print(f"raw_description:  {_clean(row.raw_description)}")
        if row.raw_tooltip:
            print(f"raw_tooltip:      {_clean(row.raw_tooltip)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
