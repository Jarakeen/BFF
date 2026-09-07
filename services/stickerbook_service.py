from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ARMOR_TYPES = {1: "Light", 2: "Medium", 3: "Heavy"}
EQUIP_TYPES = {
    1: "Head",
    2: "Necklace",
    3: "Chest",
    4: "Shoulders",
    5: "One Hand",
    6: "Two Hand",
    7: "Off Hand",
    8: "Waist",
    9: "Legs",
    10: "Feet",
    12: "Ring",
    13: "Hands",
    14: "Main Hand",
}
WEAPON_TYPES = {
    1: "Axe",
    2: "Mace",
    3: "Sword",
    4: "Two-Handed Sword",
    5: "Two-Handed Axe",
    6: "Two-Handed Mace",
    8: "Bow",
    9: "Restoration Staff",
    11: "Dagger",
    12: "Inferno Staff",
    13: "Ice Staff",
    14: "Shield",
    15: "Lightning Staff",
}

STICKERBOOK_BUCKETS = (
    "Arena",
    "Dungeon",
    "Trial",
    "Overland",
    "PvP",
    "Monster",
    "Mythic",
    "Class",
    "Other",
)

# ESO's Item Set Collection tracks dropped/bound set gear that can be
# reconstructed. Crafted sets are intentionally not part of the in-game
# stickerbook, so BFF keeps them out of completion totals too.
_CRAFTED_TOKENS = ("craft", "crafted", "craftable")

# ESO source text sometimes carries game-client color tags. Normal ESO tags use
# exactly six hex digits. A few source rows contain malformed 7/8-digit tags with
# a trailing delimiter, so accept those only when the delimiter proves where the
# tag ends. This avoids consuming a legitimate leading A-F character from text,
# e.g. ``|c00FF00Color`` must become ``Color``, not ``olor``.
_ESO_COLOR_OPEN_RE = re.compile(
    r"\|c(?:[0-9a-fA-F]{7,8}\||[0-9a-fA-F]{6}\|?)",
    re.IGNORECASE,
)
_ESO_COLOR_RESET_RE = re.compile(r"\|r", re.IGNORECASE)

# Standard dropped five-piece sets are reconstructable in every ordinary weapon
# type. Some imports only preserve armor/jewelry structural rows, so Stickerbook
# fills missing weapon identities at the collection boundary without mutating the
# canonical source tables. Special sets keep their source-defined shapes.
_STANDARD_WEAPON_EQUIP = {
    1: 5,
    2: 5,
    3: 5,
    4: 6,
    5: 6,
    6: 6,
    8: 6,
    9: 6,
    11: 5,
    12: 6,
    13: 6,
    14: 5,
    15: 6,
}
_STANDARD_WEAPON_BUCKETS = {"Dungeon", "Trial", "Overland", "PvP", "Class", "Other"}


def clean_eso_text(value: object) -> str:
    text = str(value or "")
    text = _ESO_COLOR_OPEN_RE.sub("", text)
    text = _ESO_COLOR_RESET_RE.sub("", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class StickerbookPiece:
    set_id: int
    piece_key: str
    label: str
    group: str
    equip_type: int | None
    armor_type: int | None
    weapon_type: int | None
    collected: bool


class StickerbookService:
    """Profile-aware ownership ledger over the canonical dropped-set catalog."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _tables(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stickerbook_progress (
                    profile_id TEXT NOT NULL,
                    set_id INTEGER NOT NULL,
                    piece_key TEXT NOT NULL,
                    collected INTEGER NOT NULL DEFAULT 0,
                    acquired_on TEXT,
                    notes TEXT,
                    PRIMARY KEY (profile_id, set_id, piece_key)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stickerbook_progress_profile "
                "ON stickerbook_progress(profile_id, collected)"
            )
            connection.commit()

    @staticmethod
    def piece_key(set_id: int, equip_type, armor_type, weapon_type) -> str:
        return f"{int(set_id)}:{int(equip_type or 0)}:{int(armor_type or 0)}:{int(weapon_type or 0)}"

    @staticmethod
    def piece_label(equip_type, armor_type, weapon_type) -> tuple[str, str]:
        weapon_id = int(weapon_type or 0)
        armor_id = int(armor_type or 0)
        equip_id = int(equip_type or 0)

        if weapon_id > 0:
            return WEAPON_TYPES.get(weapon_id, f"Weapon Type {weapon_id}"), "Weapons"
        if equip_id in {2, 12}:
            return EQUIP_TYPES.get(equip_id, f"Jewelry Slot {equip_id}"), "Jewelry"
        if equip_id in {1, 3, 4, 8, 9, 10, 13}:
            slot = EQUIP_TYPES[equip_id]
            weight = ARMOR_TYPES.get(armor_id, "")
            return (f"{slot} · {weight}" if weight else slot), "Armor"

        # Preserve unexpected canonical structures rather than pretending they
        # are armor. This makes source-data gaps visible without losing the row.
        slot = EQUIP_TYPES.get(equip_id, f"Equipment Slot {equip_id}")
        return slot, "Other"

    def profiles(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT profile_id FROM stickerbook_progress ORDER BY profile_id COLLATE NOCASE"
            ).fetchall()
        values = [clean_eso_text(row[0]) for row in rows if clean_eso_text(row[0])]
        return values or ["Default"]

    def _source_by_set(self, connection: sqlite3.Connection) -> dict[int, tuple[str, str]]:
        tables = self._tables(connection)
        if not {"content", "content_sets"}.issubset(tables):
            return {}
        rows = connection.execute(
            """
            SELECT cs.set_id, c.content_type, c.name
            FROM content_sets cs
            JOIN content c ON c.id = cs.content_id
            ORDER BY c.name COLLATE NOCASE
            """
        ).fetchall()
        result: dict[int, tuple[str, str]] = {}
        for set_id, content_type, name in rows:
            try:
                key = int(set_id)
            except (TypeError, ValueError):
                continue
            if key not in result:
                result[key] = (clean_eso_text(content_type), clean_eso_text(name))
        return result

    @staticmethod
    def _is_stickerbook_set(category: str, content_type: str, source: str) -> bool:
        text = " ".join((category, content_type, source)).casefold()
        return not any(token in text for token in _CRAFTED_TOKENS)

    @staticmethod
    def _bucket(category: str, content_type: str, source: str) -> str:
        text = " ".join((category, content_type, source)).casefold()
        if "mythic" in text:
            return "Mythic"
        if "monster" in text:
            return "Monster"
        if "class" in text or "infinite archive" in text:
            return "Class"
        if "arena" in text or "maelstrom" in text or "dragonstar" in text or "vateshran" in text:
            return "Arena"
        if "trial" in text:
            return "Trial"
        if "dungeon" in text:
            return "Dungeon"
        if "cyrodiil" in text or "pvp" in text or "alliance war" in text or "battleground" in text:
            return "PvP"
        if "overland" in text or "zone" in text or "world" in text:
            return "Overland"
        return "Other"

    @staticmethod
    def _missing_standard_weapon_types(
        *,
        bucket: str,
        max_equip_count: int | None,
        existing_weapon_types: set[int],
    ) -> tuple[int, ...]:
        try:
            max_count = int(max_equip_count or 0)
        except (TypeError, ValueError):
            max_count = 0
        if bucket not in _STANDARD_WEAPON_BUCKETS or max_count < 5:
            return ()
        return tuple(
            weapon_type
            for weapon_type in WEAPON_TYPES
            if weapon_type not in existing_weapon_types
        )

    def sets(self, profile_id: str = "Default") -> list[dict]:
        profile = clean_eso_text(profile_id) or "Default"
        with self._connect() as connection:
            tables = self._tables(connection)
            if not {"gear_set", "gear_set_piece"}.issubset(tables):
                return []
            source_map = self._source_by_set(connection)
            rows = connection.execute(
                """
                SELECT gs.id, gs.name, COALESCE(gs.category, '') AS category,
                       gs.max_equip_count,
                       COUNT(gp.id) AS piece_count,
                       GROUP_CONCAT(DISTINCT CASE WHEN COALESCE(gp.weapon_type, 0) > 0 THEN gp.weapon_type END) AS weapon_types,
                       SUM(CASE WHEN COALESCE(sp.collected, 0) = 1 THEN 1 ELSE 0 END) AS collected_count
                FROM gear_set gs
                JOIN gear_set_piece gp ON gp.set_id = gs.id
                LEFT JOIN stickerbook_progress sp
                  ON sp.set_id = gs.id
                 AND sp.piece_key = CAST(gs.id AS TEXT) || ':' || CAST(COALESCE(gp.equip_type, 0) AS TEXT)
                      || ':' || CAST(COALESCE(gp.armor_type, 0) AS TEXT)
                      || ':' || CAST(COALESCE(gp.weapon_type, 0) AS TEXT)
                 AND sp.profile_id = ?
                GROUP BY gs.id, gs.name, gs.category, gs.max_equip_count
                ORDER BY gs.name COLLATE NOCASE
                """,
                (profile,),
            ).fetchall()
            progress_rows = connection.execute(
                """
                SELECT set_id, piece_key
                FROM stickerbook_progress
                WHERE profile_id = ? AND collected = 1
                """,
                (profile,),
            ).fetchall()

        collected_keys_by_set: dict[int, set[str]] = {}
        for set_id, piece_key in progress_rows:
            collected_keys_by_set.setdefault(int(set_id), set()).add(str(piece_key))

        result = []
        for row in rows:
            set_id = int(row["id"])
            content_type, source = source_map.get(set_id, ("", ""))
            category = clean_eso_text(row["category"])
            content_type = clean_eso_text(content_type)
            source = clean_eso_text(source)
            if not self._is_stickerbook_set(category, content_type, source):
                continue
            bucket = self._bucket(category, content_type, source)
            existing_weapon_types = {
                int(value)
                for value in str(row["weapon_types"] or "").split(",")
                if value.strip().isdigit()
            }
            missing_weapons = self._missing_standard_weapon_types(
                bucket=bucket,
                max_equip_count=row["max_equip_count"],
                existing_weapon_types=existing_weapon_types,
            )
            synthetic_collected = 0
            owned_keys = collected_keys_by_set.get(set_id, set())
            for weapon_type in missing_weapons:
                key = self.piece_key(
                    set_id,
                    _STANDARD_WEAPON_EQUIP[weapon_type],
                    0,
                    weapon_type,
                )
                if key in owned_keys:
                    synthetic_collected += 1
            result.append(
                {
                    "id": set_id,
                    "name": clean_eso_text(row["name"]),
                    "category": category,
                    "bucket": bucket,
                    "source": source,
                    "content_type": content_type,
                    "collected": int(row["collected_count"] or 0) + synthetic_collected,
                    "total": int(row["piece_count"] or 0) + len(missing_weapons),
                }
            )
        return result

    def pieces(self, set_id: int, profile_id: str = "Default") -> list[StickerbookPiece]:
        profile = clean_eso_text(profile_id) or "Default"
        set_id = int(set_id)
        with self._connect() as connection:
            source_map = self._source_by_set(connection)
            metadata = connection.execute(
                """
                SELECT COALESCE(category, '') AS category, max_equip_count
                FROM gear_set
                WHERE id = ?
                """,
                (set_id,),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT equip_type, armor_type, weapon_type
                FROM gear_set_piece
                WHERE set_id = ?
                ORDER BY equip_type, armor_type, weapon_type
                """,
                (set_id,),
            ).fetchall()
            owned_rows = connection.execute(
                """
                SELECT piece_key
                FROM stickerbook_progress
                WHERE profile_id = ? AND set_id = ? AND collected = 1
                """,
                (profile, set_id),
            ).fetchall()

        owned_keys = {str(row[0]) for row in owned_rows}
        piece_rows = [
            (
                row["equip_type"],
                row["armor_type"],
                row["weapon_type"],
            )
            for row in rows
        ]

        if metadata is not None:
            content_type, source = source_map.get(set_id, ("", ""))
            category = clean_eso_text(metadata["category"])
            bucket = self._bucket(category, clean_eso_text(content_type), clean_eso_text(source))
            existing_weapon_types = {
                int(weapon_type or 0)
                for _equip_type, _armor_type, weapon_type in piece_rows
                if int(weapon_type or 0) > 0
            }
            for weapon_type in self._missing_standard_weapon_types(
                bucket=bucket,
                max_equip_count=metadata["max_equip_count"],
                existing_weapon_types=existing_weapon_types,
            ):
                piece_rows.append(
                    (_STANDARD_WEAPON_EQUIP[weapon_type], 0, weapon_type)
                )

        pieces: list[StickerbookPiece] = []
        for equip_type, armor_type, weapon_type in piece_rows:
            key = self.piece_key(set_id, equip_type, armor_type, weapon_type)
            label, group = self.piece_label(equip_type, armor_type, weapon_type)
            pieces.append(
                StickerbookPiece(
                    set_id=set_id,
                    piece_key=key,
                    label=clean_eso_text(label),
                    group=group,
                    equip_type=equip_type,
                    armor_type=armor_type,
                    weapon_type=weapon_type,
                    collected=key in owned_keys,
                )
            )

        group_order = {"Armor": 1, "Weapons": 2, "Jewelry": 3, "Other": 4}
        pieces.sort(
            key=lambda piece: (
                group_order.get(piece.group, 9),
                int(piece.equip_type or 0),
                int(piece.armor_type or 0),
                int(piece.weapon_type or 0),
            )
        )
        return pieces

    def set_collected(self, profile_id: str, set_id: int, piece_key: str, collected: bool) -> None:
        profile = clean_eso_text(profile_id) or "Default"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stickerbook_progress(profile_id, set_id, piece_key, collected)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(profile_id, set_id, piece_key)
                DO UPDATE SET collected = excluded.collected
                """,
                (profile, int(set_id), str(piece_key), int(bool(collected))),
            )
            connection.commit()

    def summary(self, profile_id: str = "Default", bucket: str | None = None) -> tuple[int, int]:
        rows = self.sets(profile_id)
        if bucket:
            rows = [row for row in rows if row["bucket"] == bucket]
        return sum(row["collected"] for row in rows), sum(row["total"] for row in rows)

    def bonuses(self, set_id: int) -> list[tuple[int, str]]:
        with self._connect() as connection:
            if "gear_set_bonus" not in self._tables(connection):
                return []
            rows = connection.execute(
                """
                SELECT piece_count, description
                FROM gear_set_bonus
                WHERE set_id = ? AND description IS NOT NULL AND TRIM(description) <> ''
                ORDER BY piece_count, id
                """,
                (int(set_id),),
            ).fetchall()
        return [
            (int(row[0]), clean_eso_text(row[1]))
            for row in rows
            if clean_eso_text(row[1])
        ]

    def export_csv(self, target: str | Path, profile_id: str = "Default") -> Path:
        path = Path(target)
        rows = self.sets(profile_id)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Profile", "Set", "Category", "Source", "Collected", "Total", "Percent"])
            for row in rows:
                percent = round(100 * row["collected"] / row["total"], 1) if row["total"] else 0.0
                writer.writerow([
                    clean_eso_text(profile_id), row["name"], row["bucket"], row["source"],
                    row["collected"], row["total"], percent,
                ])
        return path
