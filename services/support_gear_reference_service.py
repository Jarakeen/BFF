from __future__ import annotations

"""User-owned support-gear idea board for Top Gear."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from engine.config import get_user_database_path
from services.eso_database import EsoDatabase


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class SupportGearReference:
    reference_id: str
    role: str
    set_name: str
    coverage: str
    notes: str = ""
    seeded: bool = False

    def __post_init__(self) -> None:
        reference_id = _clean(self.reference_id)
        role = _clean(self.role).casefold()
        set_name = _clean(self.set_name)
        coverage = _clean(self.coverage)
        notes = _clean(self.notes)
        if not reference_id:
            raise ValueError("support gear reference requires reference_id")
        if role not in {"healer", "tank"}:
            raise ValueError("support gear role must be healer or tank")
        if not set_name:
            raise ValueError("support gear reference requires set_name")
        if not coverage:
            raise ValueError("support gear reference requires coverage")
        if not isinstance(self.seeded, bool):
            raise TypeError("support gear seeded flag must be boolean")
        object.__setattr__(self, "reference_id", reference_id)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "set_name", set_name)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "notes", notes)


_CURRENT_META_SEEDS: tuple[tuple[str, str, str, str], ...] = (
    ("healer", "Spell Power Cure", "Major Courage", "Core damage-support option when Major Courage is not supplied elsewhere."),
    ("healer", "Powerful Assault", "Unique Weapon / Spell Damage", "Common offensive support pairing; activation still depends on Assault-skill use."),
    ("healer", "Pillager's Profit", "Group Ultimate generation", "Common trial support set for feeding group Ultimate."),
    ("healer", "Roaring Opportunist", "Major Slayer", "Usually paired with Jorvuld's Guidance when the group is not using Slayer stacks."),
    ("healer", "Jorvuld's Guidance", "Extends Major / Minor buffs", "Common Roaring Opportunist partner; useful where longer support-buff duration matters."),
    ("healer", "Master Architect", "Major Slayer", "Burst-oriented Slayer option; still useful for selected groups and encounters."),
    ("healer", "Ozezan the Inferno", "Minor Vitality + unique Armor support", "Monster-set support option that rewards active healing / overhealing."),
    ("healer", "Symphony of Blades", "Group resource sustain", "Monster-set sustain option for Magicka / Stamina restoration."),
    ("healer", "Xoryn's Masterpiece", "Unique group damage support", "Flexible support set seen in modern organized groups."),
    ("tank", "Lucent Echoes", "Group Critical Damage / Critical Healing", "Modern tank support option; offensive value while the wearer is above 50% Health."),
    ("tank", "Frozen Watcher", "Chilled pressure / Major Brittle support", "Warden-tank option for aggressive Chilled application and Brittle-oriented group support."),
    ("tank", "Pearlescent Ward", "Unique group damage / mitigation", "Scales between offensive support and mitigation as group members die."),
    ("tank", "Xoryn's Masterpiece", "Unique group damage support", "Flexible support set that can sit on a tank depending on the comp."),
    ("tank", "Saxhleel Champion", "Major Force", "Converts Ultimate use into Major Force support."),
    ("tank", "Turning Tide", "Major Vulnerability", "Tank-owned Major Vulnerability option; situational when the group already has strong alternative coverage."),
    ("tank", "Stonehulk", "Major Vulnerability support", "Situational Major Vulnerability support option, especially when paired around encounter/group coverage needs."),
    ("tank", "Archdruid Devyric", "Major Vulnerability", "Monster-set Major Vulnerability option for compositions that need another source."),
    ("tank", "Crimson Oath's Rive", "Unique Armor reduction", "Group penetration support through enemy Armor reduction."),
    ("tank", "Claw of Yolnahkriin", "Minor Courage", "Classic tank source of Minor Courage when the comp still needs it."),
    ("tank", "War Machine", "Major Slayer", "Tank-accessible Slayer option for specific group plans."),
    ("tank", "Arkasis's Genius", "Group Ultimate generation", "Potion-triggered Ultimate support for selected strategies."),
    ("tank", "Cryptcannon Vestments", "Ultimate transfer / support", "Mythic support option for funneling Ultimate value into an ally."),
)


class SupportGearReferenceService:
    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path or get_user_database_path())
        self.db = EsoDatabase(self.database_path)
        self._ensure_schema()
        self._seed_if_empty()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS support_gear_reference (
                reference_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                set_name TEXT NOT NULL,
                coverage TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                seeded INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK (role IN ('healer', 'tank')),
                CHECK (seeded IN (0, 1))
            )
            """
        )
        self.db.commit()

    @staticmethod
    def _seed_id(role: str, set_name: str) -> str:
        return str(
            uuid5(
                NAMESPACE_URL,
                f"foundrydock:support-gear:{_clean(role).casefold()}:{_clean(set_name).casefold()}",
            )
        )

    def _seed_if_empty(self) -> None:
        row = self.db.execute(
            "SELECT COUNT(*) AS count FROM support_gear_reference"
        ).fetchone()
        if row is not None and int(row["count"]) > 0:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for role, set_name, coverage, notes in _CURRENT_META_SEEDS:
            self.db.execute(
                """
                INSERT INTO support_gear_reference (
                    reference_id, role, set_name, coverage, notes, seeded,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    self._seed_id(role, set_name),
                    role,
                    set_name,
                    coverage,
                    notes,
                    now,
                    now,
                ),
            )
        self.db.commit()

    def list_for_role(self, role: str) -> tuple[SupportGearReference, ...]:
        normalized = _clean(role).casefold()
        if normalized not in {"healer", "tank"}:
            raise ValueError("support gear role must be healer or tank")
        rows = self.db.execute(
            """
            SELECT reference_id, role, set_name, coverage, notes, seeded
            FROM support_gear_reference
            WHERE role = ?
            ORDER BY set_name COLLATE NOCASE, reference_id
            """,
            (normalized,),
        ).fetchall()
        return tuple(
            SupportGearReference(
                reference_id=str(row["reference_id"] or ""),
                role=str(row["role"] or ""),
                set_name=str(row["set_name"] or ""),
                coverage=str(row["coverage"] or ""),
                notes=str(row["notes"] or ""),
                seeded=bool(int(row["seeded"] or 0)),
            )
            for row in rows
        )

    def save(self, reference: SupportGearReference) -> SupportGearReference:
        if not isinstance(reference, SupportGearReference):
            raise TypeError("support gear save requires SupportGearReference")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        existing = self.db.execute(
            "SELECT created_at FROM support_gear_reference WHERE reference_id = ?",
            (reference.reference_id,),
        ).fetchone()
        created_at = str(existing["created_at"]) if existing is not None else now
        self.db.execute(
            """
            INSERT INTO support_gear_reference (
                reference_id, role, set_name, coverage, notes, seeded,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(reference_id) DO UPDATE SET
                role = excluded.role,
                set_name = excluded.set_name,
                coverage = excluded.coverage,
                notes = excluded.notes,
                seeded = excluded.seeded,
                updated_at = excluded.updated_at
            """,
            (
                reference.reference_id,
                reference.role,
                reference.set_name,
                reference.coverage,
                reference.notes,
                1 if reference.seeded else 0,
                created_at,
                now,
            ),
        )
        self.db.commit()
        return reference

    def create(
        self,
        *,
        role: str,
        set_name: str,
        coverage: str,
        notes: str = "",
    ) -> SupportGearReference:
        reference = SupportGearReference(
            reference_id=self._seed_id(role, set_name),
            role=role,
            set_name=set_name,
            coverage=coverage,
            notes=notes,
            seeded=False,
        )
        return self.save(reference)

    def delete(self, reference_id: str) -> None:
        key = _clean(reference_id)
        if not key:
            raise ValueError("support gear delete requires reference_id")
        self.db.execute(
            "DELETE FROM support_gear_reference WHERE reference_id = ?",
            (key,),
        )
        self.db.commit()


__all__ = ["SupportGearReference", "SupportGearReferenceService"]
