from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


_ARMOR_TYPE_LABELS = {
    1: "Light",
    2: "Medium",
    3: "Heavy",
}

_BONUS_FACETS = (
    ("Max Health", ("max health",)),
    ("Max Magicka", ("max magicka",)),
    ("Max Stamina", ("max stamina",)),
    ("Health Recovery", ("health recovery",)),
    ("Magicka Recovery", ("magicka recovery",)),
    ("Stamina Recovery", ("stamina recovery",)),
    ("Weapon / Spell Damage", ("weapon damage", "spell damage", "weapon and spell damage")),
    ("Critical", ("critical",)),
    ("Penetration", ("penetration",)),
    ("Armor / Resistance", ("armor", "resistance")),
    ("Healing", ("healing", "heals", "heal ")),
    ("Damage", ("damage",)),
)

_OPTIONAL_METADATA_COLUMNS = {
    "acquisition_type": ("acquisition_type", "activity_type", "source_type", "set_type"),
}

# Practical lookup buckets requested by the app owner. These answer the useful
# question: can I make it, buy/farm it in the world, farm/reconstruct it from
# PvE group content, or deal with Cyrodiil-specific acquisition?
_ACQUISITION_TYPES = (
    "Crafted",
    "Overland",
    "Dungeon / Trial",
    "Cyrodiil",
)


class GearLookupPage(FoundryPage):
    """Read-only browser for the canonical ESO gear-set catalog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.database_path = get_data_dir() / "eso.db"
        self._sets: list[dict] = []
        self._metadata_columns: dict[str, str | None] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Gear Lookup",
            subtitle="Find a set quickly, inspect its canonical piece bonuses, and get back to the actual problem.",
            department="TOOLS • GEAR LOOKUP",
        )
        self.set_header(self.header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search set name, acquisition, source, or bonus text...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_sets)
        self.header.add_context_widget(self._context_field("SEARCH", self.search))

        self.weight = self._filter_combo("All Weights")
        self.bonus = self._filter_combo("Any Bonus")
        self.acquisition_type = self._filter_combo("All Acquisition Types")

        filter_card = FoundryCard("Filters", "filter")
        filter_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filter_card.body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filter_card.set_body_margins(10, 5, 10, 6)
        filter_card.setMaximumHeight(96)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        filter_row.addWidget(self._context_field("WEIGHT", self.weight), 1)
        filter_row.addWidget(self._context_field("BONUS", self.bonus), 1)
        filter_row.addWidget(self._context_field("ACQUISITION", self.acquisition_type), 1)
        filter_card.addLayout(filter_row)
        self.workspace_layout.addWidget(filter_card, 0)

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(8)

        index_card = FoundryCard("Gear Sets", "search").set_watermark("compass", 0.04)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self._show_selected)
        index_card.addWidget(self.results)
        workspace.addWidget(index_card, 2)

        detail_card = FoundryCard("Set Details", "set").set_watermark("compass", 0.05)
        self.set_name = QLabel("Select a gear set")
        self.set_name.setProperty("heroTitle", True)
        self.set_meta = QLabel()
        self.set_meta.setWordWrap(True)
        self.bonuses = QLabel()
        self.bonuses.setWordWrap(True)
        self.bonuses.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_card.addWidget(self.set_name)
        detail_card.addWidget(self.set_meta)
        detail_card.addWidget(self.bonuses)
        detail_card.addStretch(1)
        workspace.addWidget(detail_card, 5)

        host = QWidget()
        host.setLayout(workspace)
        self.add_workspace(host)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _filter_combo(self, all_label: str) -> QComboBox:
        combo = QComboBox()
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.addItem(all_label, "")
        combo.currentIndexChanged.connect(self._filter_sets)
        return combo

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    @staticmethod
    def _table_names(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    @staticmethod
    def _resolve_optional_columns(connection: sqlite3.Connection) -> dict[str, str | None]:
        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(gear_set)").fetchall()}
        resolved: dict[str, str | None] = {}
        for facet, candidates in _OPTIONAL_METADATA_COLUMNS.items():
            resolved[facet] = next((candidate for candidate in candidates if candidate in columns), None)
        return resolved

    @staticmethod
    def _normalize_acquisition(raw_value: str | None) -> str:
        value = str(raw_value or "").strip().casefold()
        if not value:
            return ""
        if any(token in value for token in ("craft", "crafted")):
            return "Crafted"
        if any(token in value for token in ("overland", "world", "zone")):
            return "Overland"
        if any(token in value for token in ("dungeon", "trial", "arena", "monster")):
            return "Dungeon / Trial"
        if any(token in value for token in ("cyrodiil", "alliance war")):
            return "Cyrodiil"
        return ""

    @staticmethod
    def _content_acquisition(
        connection: sqlite3.Connection,
        tables: set[str],
    ) -> dict[int, dict[str, object]]:
        if not {"content", "content_sets"}.issubset(tables):
            return {}

        rows = connection.execute(
            """
            SELECT
                cs.set_id,
                c.content_type,
                c.name,
                c.location
            FROM content_sets AS cs
            JOIN content AS c ON c.id = cs.content_id
            ORDER BY c.name COLLATE NOCASE
            """
        ).fetchall()

        result: dict[int, dict[str, object]] = {}
        for raw_set_id, content_type, name, location in rows:
            try:
                set_id = int(raw_set_id)
            except (TypeError, ValueError):
                continue

            entry = result.setdefault(
                set_id,
                {"acquisition_type": "", "sources": []},
            )
            content_kind = str(content_type or "").strip().casefold()
            if content_kind in {"trial", "dungeon", "arena"}:
                entry["acquisition_type"] = "Dungeon / Trial"

            source = str(name or "").strip()
            location_text = str(location or "").strip()
            if source and location_text and location_text.casefold() not in source.casefold():
                source = f"{source} • {location_text}"
            if source and source not in entry["sources"]:
                entry["sources"].append(source)

        return result

    def refresh(self) -> None:
        try:
            with sqlite3.connect(self.database_path) as connection:
                tables = self._table_names(connection)
                self._metadata_columns = self._resolve_optional_columns(connection)
                acquisition_column = self._metadata_columns.get("acquisition_type")
                acquisition_select = (
                    f", gs.{acquisition_column} AS stored_acquisition_type"
                    if acquisition_column
                    else ", NULL AS stored_acquisition_type"
                )

                rows = connection.execute(
                    f"""
                    SELECT
                        gs.id,
                        gs.name,
                        COALESCE(gs.category, ''),
                        gs.max_equip_count,
                        GROUP_CONCAT(DISTINCT gp.armor_type)
                        {acquisition_select}
                    FROM gear_set AS gs
                    LEFT JOIN gear_set_piece AS gp ON gp.set_id = gs.id
                    GROUP BY gs.id
                    ORDER BY gs.name COLLATE NOCASE
                    """
                ).fetchall()

                bonus_rows = connection.execute(
                    """
                    SELECT set_id, description
                    FROM gear_set_bonus
                    WHERE description IS NOT NULL AND TRIM(description) <> ''
                    ORDER BY set_id, piece_count, id
                    """
                ).fetchall()

                content_acquisition = self._content_acquisition(connection, tables)
        except sqlite3.Error as exc:
            self._sets = []
            self.results.clear()
            self.status.error(f"Gear catalog unavailable: {exc}")
            return

        bonuses_by_set: dict[int, list[str]] = {}
        for set_id, description in bonus_rows:
            bonuses_by_set.setdefault(int(set_id), []).append(str(description))

        self._sets = []
        for row in rows:
            set_id, name, category, max_equip_count, armor_csv, stored_acquisition = row
            set_id = int(set_id)
            armor_types = {
                int(value)
                for value in str(armor_csv or "").split(",")
                if value.strip().isdigit() and int(value) in _ARMOR_TYPE_LABELS
            }

            content_info = content_acquisition.get(set_id, {})
            acquisition_type = str(content_info.get("acquisition_type") or "")
            if not acquisition_type:
                acquisition_type = self._normalize_acquisition(str(stored_acquisition or ""))
            if not acquisition_type:
                acquisition_type = self._normalize_acquisition(str(category or ""))

            self._sets.append(
                {
                    "id": set_id,
                    "name": str(name),
                    "category": str(category or ""),
                    "max_equip_count": max_equip_count,
                    "armor_types": armor_types,
                    "bonus_texts": bonuses_by_set.get(set_id, []),
                    "acquisition_type": acquisition_type,
                    "sources": list(content_info.get("sources") or []),
                }
            )

        self._populate_filters()
        self._filter_sets()

        classified = sum(1 for row in self._sets if row["acquisition_type"])
        unresolved = len(self._sets) - classified
        if unresolved:
            self.status.info(
                f"Gear Lookup ready • {len(self._sets)} canonical set(s) • "
                f"{classified} acquisition-classified • {unresolved} awaiting source metadata."
            )
        else:
            self.status.info(f"Gear Lookup ready • {len(self._sets)} canonical set(s) loaded.")

    @staticmethod
    def _restore_combo(combo: QComboBox, all_label: str, values: list[str]) -> None:
        selected = str(combo.currentData() or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(all_label, "")
        for value in values:
            combo.addItem(value, value)
        if selected:
            index = combo.findData(selected)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _populate_filters(self) -> None:
        present_weights = {
            armor_type
            for row in self._sets
            for armor_type in row["armor_types"]
            if armor_type in _ARMOR_TYPE_LABELS
        }
        weight_values = [_ARMOR_TYPE_LABELS[value] for value in sorted(present_weights)]
        self._restore_combo(self.weight, "All Weights", weight_values)

        all_bonus_text = "\n".join(
            description.casefold()
            for row in self._sets
            for description in row["bonus_texts"]
        )
        bonus_values = [
            label
            for label, needles in _BONUS_FACETS
            if any(needle in all_bonus_text for needle in needles)
        ]
        self._restore_combo(self.bonus, "Any Bonus", bonus_values)

        self._restore_combo(
            self.acquisition_type,
            "All Acquisition Types",
            list(_ACQUISITION_TYPES),
        )
        self.acquisition_type.setToolTip(
            "Crafted: make it • Overland: buy/farm it • "
            "Dungeon / Trial: farm or reconstruct it • Cyrodiil: PvP-origin gear"
        )
        self.acquisition_type.setEnabled(True)

    @staticmethod
    def _bonus_facet_matches(label: str, descriptions: list[str]) -> bool:
        if not label:
            return True
        needles = next((needles for facet, needles in _BONUS_FACETS if facet == label), ())
        haystack = "\n".join(descriptions).casefold()
        return any(needle in haystack for needle in needles)

    def _filter_sets(self, *_args) -> None:
        if not hasattr(self, "results"):
            return

        query = self.search.text().strip().casefold()
        weight_label = str(self.weight.currentData() or "")
        bonus_label = str(self.bonus.currentData() or "")
        acquisition_type = str(self.acquisition_type.currentData() or "")
        weight_id = next((key for key, label in _ARMOR_TYPE_LABELS.items() if label == weight_label), None)

        current_id = None
        current = self.results.currentItem()
        if current is not None:
            current_id = current.data(Qt.ItemDataRole.UserRole)

        self.results.blockSignals(True)
        self.results.clear()
        matched = 0
        restore_row = -1

        for row in self._sets:
            if weight_id is not None and weight_id not in row["armor_types"]:
                continue
            if bonus_label and not self._bonus_facet_matches(bonus_label, row["bonus_texts"]):
                continue
            if acquisition_type and row["acquisition_type"] != acquisition_type:
                continue

            haystack = " ".join(
                [
                    row["name"],
                    row["category"],
                    row["acquisition_type"],
                    *row["sources"],
                    *row["bonus_texts"],
                ]
            ).casefold()
            if query and query not in haystack:
                continue

            item = QListWidgetItem(row["name"])
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            tooltip_bits = [row["acquisition_type"] or "Acquisition not classified"]
            tooltip_bits.extend(row["sources"])
            item.setToolTip(" • ".join(tooltip_bits))
            self.results.addItem(item)
            if row["id"] == current_id:
                restore_row = matched
            matched += 1

        self.results.blockSignals(False)

        if restore_row >= 0:
            self.results.setCurrentRow(restore_row)
        elif self.results.count():
            self.results.setCurrentRow(0)
        else:
            self.set_name.setText("No matching gear sets")
            self.set_meta.clear()
            self.bonuses.clear()

    def _show_selected(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        set_id = current.data(Qt.ItemDataRole.UserRole)
        selected = next((row for row in self._sets if row["id"] == set_id), None)
        if selected is None:
            return

        self.set_name.setText(selected["name"].upper())
        equip_text = str(selected["max_equip_count"]) if selected["max_equip_count"] is not None else "—"
        weights = ", ".join(
            _ARMOR_TYPE_LABELS[value]
            for value in sorted(selected["armor_types"])
            if value in _ARMOR_TYPE_LABELS
        ) or "—"

        metadata = [
            f"Weight: {weights}",
            f"Maximum equipped pieces: {equip_text}",
            f"Acquisition: {selected['acquisition_type'] or 'Not yet classified'}",
        ]
        if selected["sources"]:
            metadata.append(f"Source: {', '.join(selected['sources'])}")
        self.set_meta.setText("   •   ".join(metadata))

        rows = selected["bonus_texts"]
        if rows:
            try:
                with sqlite3.connect(self.database_path) as connection:
                    bonus_rows = connection.execute(
                        """
                        SELECT piece_count, description
                        FROM gear_set_bonus
                        WHERE set_id = ?
                        ORDER BY piece_count, id
                        """,
                        (set_id,),
                    ).fetchall()
            except sqlite3.Error as exc:
                bonus_rows = []
                self.status.error(f"Could not load bonuses for {selected['name']}: {exc}")

            lines = []
            for piece_count, description in bonus_rows:
                pieces = f"{piece_count} item" if int(piece_count) == 1 else f"{piece_count} items"
                lines.append(f"{pieces}: {description}")
            self.bonuses.setText("\n\n".join(lines))
        else:
            self.bonuses.setText("No canonical piece-bonus records are available for this set.")
