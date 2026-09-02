from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_MOTIF_NAME_RE = re.compile(r"^(?:Crown )?Crafting Motif\s+(\d+):\s+(.+)$", re.IGNORECASE)
_CHAPTER_PARTS = (
    "Axes",
    "Belts",
    "Boots",
    "Bows",
    "Chests",
    "Daggers",
    "Gloves",
    "Helmets",
    "Legs",
    "Maces",
    "Shields",
    "Shoulders",
    "Staves",
    "Swords",
)


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical_part(record: dict[str, Any], suffix: str) -> str:
    description = str(record.get("description") or "")
    for part in _CHAPTER_PARTS:
        if re.search(rf"\b{re.escape(part)}\b", description, re.IGNORECASE):
            if "learn" in description.casefold():
                return part

    lowered = description.casefold()
    if "crafting style" in lowered or "crafting and outfit style" in lowered:
        return "Style"

    suffix_folded = suffix.casefold()
    if suffix_folded.endswith(" style") or suffix_folded.endswith(" style, tome edition"):
        return "Style"
    for part in _CHAPTER_PARTS:
        singular = part[:-1] if part.endswith("s") else part
        if suffix_folded.endswith(part.casefold()) or suffix_folded.endswith(singular.casefold()):
            return part
    return suffix.strip()


def _style_name(record: dict[str, Any], motif_number: int, part: str, suffix: str) -> str:
    description = str(record.get("description") or "")
    patterns = (
        r"learn (?:the )?(.+?) crafting style",
        r"learn (.+?) crafting and outfit styles?",
        r"learn how to make (.+?) (?:Axes|Belts|Boots|Bows|Chests|Daggers|Gloves|Helmets|Legs|Maces|Shields|Shoulders|Staves|Swords)",
        r"learn (?:the )?(.+?) (?:Axes|Belts|Boots|Bows|Chests|Daggers|Gloves|Helmets|Legs|Maces|Shields|Shoulders|Staves|Swords)",
    )
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return match.group(1).strip().replace(" Dom.", " Dominator")

    value = suffix.strip()
    value = re.sub(r",\s*Tome Edition$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+Style$", "", value, flags=re.IGNORECASE)
    if part != "Style":
        value = re.sub(rf"\s+{re.escape(part)}$", "", value, flags=re.IGNORECASE)
        singular = part[:-1] if part.endswith("s") else part
        value = re.sub(rf"\s+{re.escape(singular)}$", "", value, flags=re.IGNORECASE)
    return value.strip().replace("Coldharbour Dom.", "Coldharbour Dominator") or f"Motif {motif_number}"


@dataclass(frozen=True)
class LearnedMotifImportSummary:
    source_records: int
    canonical_learnables: int
    full_style_books: int
    chapter_learnables: int
    collapsed_variants: int
    unresolved: tuple[str, ...]


class UespLearnedMotifImporter:
    """Import UESP motif item rows into a logical profile-trackable motif catalog.

    UESP exposes multiple physical item variants for some learnables, notably
    Crown copies and occasional renamed/abbreviated rows. BFF tracks the logical
    learnable by motif number + chapter part while preserving every raw source
    variant for provenance.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def load_export(path: str | Path) -> list[dict[str, Any]]:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected an object in {source}")
        records = payload.get("minedItemSummary")
        if not isinstance(records, list):
            raise ValueError(f"Expected a minedItemSummary list in {source}")
        if any(not isinstance(record, dict) for record in records):
            raise ValueError(f"Non-object records found in {source}")
        declared = payload.get("numRecords")
        if declared not in (None, "") and int(declared) != len(records):
            raise ValueError(
                f"numRecords={declared} does not match minedItemSummary={len(records)} in {source}"
            )
        return list(records)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS learnable_motif (
                item_id INTEGER PRIMARY KEY,
                motif_number INTEGER NOT NULL,
                style_name TEXT NOT NULL,
                part_name TEXT NOT NULL,
                is_full_style INTEGER NOT NULL CHECK (is_full_style IN (0, 1)),
                display_name TEXT NOT NULL,
                quality INTEGER,
                icon TEXT,
                description TEXT,
                source_variant_count INTEGER NOT NULL DEFAULT 1,
                source_raw_json TEXT NOT NULL,
                UNIQUE (motif_number, part_name)
            );

            CREATE INDEX IF NOT EXISTS idx_learnable_motif_style
                ON learnable_motif(style_name, motif_number, part_name);

            CREATE TABLE IF NOT EXISTS learnable_motif_progress (
                profile_name TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                learned INTEGER NOT NULL DEFAULT 0 CHECK (learned IN (0, 1)),
                learned_on TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (profile_name, item_id),
                FOREIGN KEY (item_id) REFERENCES learnable_motif(item_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_learnable_motif_progress_profile
                ON learnable_motif_progress(profile_name, learned);
            """
        )

    def run(self, *, motif_path: str | Path) -> LearnedMotifImportSummary:
        records = self.load_export(motif_path)
        unresolved: list[str] = []
        grouped: dict[tuple[int, str], list[tuple[dict[str, Any], str]]] = defaultdict(list)

        for record in records:
            name = str(record.get("name") or "").strip()
            item_id = _int(record.get("itemId"))
            match = _MOTIF_NAME_RE.match(name)
            if item_id is None or match is None:
                unresolved.append(f"Unrecognized motif row: itemId={record.get('itemId')!r} name={name!r}")
                continue
            motif_number = int(match.group(1))
            suffix = match.group(2).strip()
            part = _canonical_part(record, suffix)
            grouped[(motif_number, part)].append((record, suffix))

        full_style_books = 0
        chapter_learnables = 0

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            self._create_schema(connection)

            for (motif_number, part), variants in sorted(
                grouped.items(), key=lambda item: (item[0][0], item[0][1] != "Style", item[0][1])
            ):
                # Prefer a normal non-Crown item as the canonical physical item;
                # then lowest item id for deterministic fallback.
                variants.sort(
                    key=lambda pair: (
                        str(pair[0].get("name") or "").casefold().startswith("crown "),
                        int(pair[0].get("itemId") or 0),
                    )
                )
                canonical, suffix = variants[0]
                item_id = int(canonical["itemId"])
                style_name = _style_name(canonical, motif_number, part, suffix)
                is_full_style = 1 if part == "Style" else 0
                if is_full_style:
                    full_style_books += 1
                    display_name = f"Crafting Motif {motif_number}: {style_name} Style"
                else:
                    chapter_learnables += 1
                    display_name = f"Crafting Motif {motif_number}: {style_name} {part}"

                connection.execute(
                    """
                    INSERT INTO learnable_motif (
                        item_id, motif_number, style_name, part_name, is_full_style,
                        display_name, quality, icon, description,
                        source_variant_count, source_raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(motif_number, part_name) DO UPDATE SET
                        item_id = excluded.item_id,
                        style_name = excluded.style_name,
                        is_full_style = excluded.is_full_style,
                        display_name = excluded.display_name,
                        quality = excluded.quality,
                        icon = excluded.icon,
                        description = excluded.description,
                        source_variant_count = excluded.source_variant_count,
                        source_raw_json = excluded.source_raw_json
                    """,
                    (
                        item_id,
                        motif_number,
                        style_name,
                        part,
                        is_full_style,
                        display_name,
                        _int(canonical.get("quality")),
                        str(canonical.get("icon") or ""),
                        str(canonical.get("description") or ""),
                        len(variants),
                        json.dumps([row for row, _suffix in variants], ensure_ascii=False),
                    ),
                )

            connection.commit()

        canonical_count = len(grouped)
        return LearnedMotifImportSummary(
            source_records=len(records),
            canonical_learnables=canonical_count,
            full_style_books=full_style_books,
            chapter_learnables=chapter_learnables,
            collapsed_variants=len(records) - canonical_count,
            unresolved=tuple(unresolved),
        )
