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
        self.search.setPlaceholderText("Search set name, category, acquisition, or bonus text...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_sets)
        self.header.add_context_widget(self._context_field("SEARCH", self.search))

        self.weight = self._filter_combo("All Weights")
        self.bonus = self._filter_combo("Any Bonus")
        self.acquisition_type = self._filter_combo("All Acquisition Types")

        filter_card = FoundryCard("Filters", "⌕").set_watermark("compass", 0.025)
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        filter_row.addWidget(self._context_field("WEIGHT", self.weight), 1)
        filter_row.addWidget(self._context_field("BONUS", self.bonus), 1)
        filter_row.addWidget(self._context_field("ACQUISITION", self.acquisition_type), 1)
        filter_card.addLayout(filter_row)
        self.add_workspace(filter_card)

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(8)

        index_card = FoundryCard("Gear Sets", "⌕").set_watermark("compass", 0.04)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self._show_selected)
        index_card.addWidget(self.results)
        workspace.addWidget(index_card, 2)

        detail_card = FoundryCard("Set Details", "✦").set_watermark("compass", 0.05)
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
        combo.addItem(all_label, "")
        combo.currentIndexChanged.connect(self._filter_sets)
        return combo

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    @staticmethod
    def _resolve_optional_columns(connection: sqlite3.Connection) -> dict[str, str | None]:
        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(gear_set)").fetchall()}
        resolved: dict[str, str | None] = {}
        for facet, candidates in _OPTIONAL_METADATA_COLUMNS.items():
            resolved[facet] = next((candidate for candidate in candidates if candidate in columns), None)
        return resolved

    def refresh(self) -> None:
        try:
            with sqlite3.connect(self.database_path) as connection:
                self._metadata_columns = self._resolve_optional_columns(connection)
                acquisition_column = self._metadata_columns.get("acquisition_type")
                acquisition_select = (
                    f", gs.{acquisition_column} AS acquisition_type"
                    if acquisition_column
                    else ", NULL AS acquisition_type"
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
            set_id, name, category, max_equip_count, armor_csv, acquisition_type = row
            armor_types = {
                int(value)
                for value in str(armor_csv or "").split(",")
                if value.strip().isdigit() and int(value) in _ARMOR_TYPE_LABELS
            }
            self._sets.append(
                {
                    "id": int(set_id),
                    "name": str(name),
                    "category": str(category or ""),
                    "max_equip_count": max_equip_count,
                    "armor_types": armor_types,
                    "bonus_texts": bonuses_by_set.get(int(set_id), []),
                    "acquisition_type": str(acquisition_type or "").strip(),
                }
            )

        self._populate_filters()
        self._filter_sets()
        if not self._metadata_columns.get("acquisition_type"):
            self.status.info(
                f"Gear Lookup ready • {len(self._sets)} canonical set(s) loaded • "
                "catalog does not yet store acquisition type."
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

        self._populate_acquisition_combo()

    def _populate_acquisition_combo(self) -> None:
        combo = self.acquisition_type
        column = self._metadata_columns.get("acquisition_type")
        combo.blockSignals(True)
        combo.clear()
        if not column:
            combo.addItem("Acquisition data unavailable", "")
            combo.setEnabled(False)
            combo.blockSignals(False)
            return

        selected = str(combo.currentData() or "")
        values = sorted({row["acquisition_type"] for row in self._sets if row["acquisition_type"]}, key=str.casefold)
        combo.addItem("All Acquisition Types", "")
        for value in values:
            combo.addItem(value, value)
        if selected:
            index = combo.findData(selected)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.setEnabled(True)
        combo.blockSignals(False)

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
                    *row["bonus_texts"],
                ]
            ).casefold()
            if query and query not in haystack:
                continue

            item = QListWidgetItem(row["name"])
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            item.setToolTip(row["category"] or "Uncategorized")
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
        category_text = selected["category"] or "Uncategorized"
        equip_text = str(selected["max_equip_count"]) if selected["max_equip_count"] is not None else "—"
        weights = ", ".join(
            _ARMOR_TYPE_LABELS[value]
            for value in sorted(selected["armor_types"])
            if value in _ARMOR_TYPE_LABELS
        ) or "—"

        metadata = [
            f"Category: {category_text}",
            f"Weight: {weights}",
            f"Maximum equipped pieces: {equip_text}",
        ]
        if selected["acquisition_type"]:
            metadata.append(f"Acquisition: {selected['acquisition_type']}")
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
