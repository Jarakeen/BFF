from __future__ import annotations

"""Search support for the Raid Engine Boss Guide / Mechanics page.

The search box filters the boss selector using persisted encounter identity,
abilities, phases, and reviewed canonical mechanic facts. It remains a read-only
projection: search never invents mechanic semantics or writes encounter data.
"""

from pathlib import Path
import sqlite3

from PySide6.QtWidgets import QLineEdit

from ui.mechanics_boss_map_support import PAIR_ID, PAIR_MEMBERS


_INSTALLED = False


def searchable_encounter_ids(database: str | Path, query: str) -> set[str]:
    """Return encounter ids whose persisted boss/mechanic text matches query."""

    text = str(query or "").strip().casefold()
    if not text:
        return set()

    path = Path(database)
    if not path.exists():
        return set()

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required = {"content", "encounter", "encounter_ability", "encounter_phase"}
        if not required.issubset(tables):
            return set()

        fact_clause = ""
        if "encounter_canonical_fact" in tables:
            fact_clause = """
                OR EXISTS (
                    SELECT 1
                    FROM encounter_canonical_fact AS f
                    WHERE f.encounter_id = e.id
                      AND f.canonical_kind IN (
                          'mechanic_detail', 'mechanic_presence',
                          'phase', 'phase_transition'
                      )
                      AND (
                          LOWER(COALESCE(f.fact_key, '')) LIKE ?
                          OR LOWER(COALESCE(f.payload_json, '')) LIKE ?
                      )
                )
            """

        pattern = f"%{text}%"
        parameters = [pattern] * 12
        if fact_clause:
            parameters.extend([pattern, pattern])

        rows = connection.execute(
            f"""
            SELECT DISTINCT e.id
            FROM encounter AS e
            JOIN content AS c ON c.id = e.content_id
            WHERE
                LOWER(COALESCE(e.name, '')) LIKE ?
                OR LOWER(COALESCE(e.summary, '')) LIKE ?
                OR LOWER(COALESCE(e.location, '')) LIKE ?
                OR LOWER(COALESCE(c.name, '')) LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM encounter_ability AS a
                    WHERE a.encounter_id = e.id
                      AND (
                          LOWER(COALESCE(a.name, '')) LIKE ?
                          OR LOWER(COALESCE(a.description, '')) LIKE ?
                          OR LOWER(COALESCE(a.interrupt_note, '')) LIKE ?
                          OR LOWER(COALESCE(a.source_section, '')) LIKE ?
                      )
                )
                OR EXISTS (
                    SELECT 1
                    FROM encounter_phase AS p
                    WHERE p.encounter_id = e.id
                      AND (
                          LOWER(COALESCE(p.label, '')) LIKE ?
                          OR LOWER(COALESCE(p.threshold, '')) LIKE ?
                          OR LOWER(COALESCE(p.description, '')) LIKE ?
                          OR LOWER(COALESCE(p.source_section, '')) LIKE ?
                      )
                )
                {fact_clause}
            ORDER BY e.id
            """,
            tuple(parameters),
        ).fetchall()
        result = {str(row["id"]) for row in rows}
        if result.intersection(PAIR_MEMBERS):
            result.add(PAIR_ID)
        return result
    finally:
        connection.close()


def _summary_matches(row, query: str) -> bool:
    text = str(query or "").strip().casefold()
    if not text:
        return True
    haystack = " ".join(
        (
            str(getattr(row, "name", "") or ""),
            str(getattr(row, "content_name", "") or ""),
            str(getattr(row, "location", "") or ""),
        )
    ).casefold()
    return text in haystack


def install() -> None:
    """Add a global boss/mechanic search box to Mechanics before page creation."""

    global _INSTALLED
    if _INSTALLED:
        return

    from ui.mechanics_page import MechanicsPage

    original_init = MechanicsPage.__init__
    original_populate = MechanicsPage._populate_boss_combo
    original_show_all = MechanicsPage._show_all_bosses

    def populate_with_search(self, preferred_encounter_id: str | None = None) -> None:
        search = getattr(self, "mechanic_search", None)
        query = search.text().strip() if search is not None else ""
        if not query or self.guide_service is None:
            original_populate(self, preferred_encounter_id)
            return

        content_id = self.trial_combo.currentData()
        matches = searchable_encounter_ids(self.guide_service.database, query)
        rows = [
            row
            for row in self._guide_summaries
            if (content_id is None or row.content_id == content_id)
            and (row.encounter_id in matches or _summary_matches(row, query))
        ]
        current = preferred_encounter_id or self.boss_combo.currentData()

        self.boss_combo.blockSignals(True)
        self.boss_combo.clear()
        for row in rows:
            self.boss_combo.addItem(row.name, row.encounter_id)
        self.boss_combo.blockSignals(False)

        if current is not None:
            index = self.boss_combo.findData(current)
            if index >= 0:
                self.boss_combo.setCurrentIndex(index)
        if self.boss_combo.count() > 0 and self.boss_combo.currentIndex() < 0:
            self.boss_combo.setCurrentIndex(0)
        self._boss_changed(self.boss_combo.currentIndex())

        if self.boss_combo.count() == 0 and hasattr(self, "status"):
            self.status.info(f'No boss or mechanic matches "{query}".')

    def init_with_search(self, *args, **kwargs) -> None:
        original_init(self, *args, **kwargs)
        self.mechanic_search = QLineEdit()
        self.mechanic_search.setClearButtonEnabled(True)
        self.mechanic_search.setMinimumWidth(280)
        self.mechanic_search.setPlaceholderText(
            "Search bosses, abilities, mechanics, descriptions..."
        )
        self.mechanic_search.setToolTip(
            "Search boss names, content, abilities, descriptions, phases, and reviewed canonical mechanics."
        )
        self.header.add_context_widget(
            self._context_field("SEARCH BOSS MECHS", self.mechanic_search)
        )
        self.mechanic_search.textChanged.connect(
            lambda _text: self._populate_boss_combo()
        )

    def show_all_with_search(self) -> None:
        search = getattr(self, "mechanic_search", None)
        if search is not None:
            search.clear()
        original_show_all(self)

    MechanicsPage._populate_boss_combo = populate_with_search
    MechanicsPage._show_all_bosses = show_all_with_search
    MechanicsPage.__init__ = init_with_search
    _INSTALLED = True
