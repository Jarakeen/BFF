from __future__ import annotations

"""Mechanics-page support for paired encounters and per-boss Raid Maps.

The raw UESP corpus keeps Lylanar and Turlassil as separate boss records. Raid
operations do not: they are one mandatory encounter. This layer preserves both
raw records while presenting one merged boss-guide page.
"""

from dataclasses import replace

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.encounter_boss_guide import (
    BossGuideEncounterSummary,
    EncounterBossGuide,
    EncounterBossGuideService,
)
from services.encounter_raid_map_store import EncounterRaidMapStore


_INSTALLED = False
PAIR_ID = "lylanar_turlassil"
PAIR_CONTENT_ID = "dreadsail_reef"
PAIR_MEMBERS = ("lylanar", "turlassil")
PAIR_NAME = "Lylanar and Turlassil"
PAIR_OBJECTIVE_ALIASES = {
    "lylanar",
    "turlassil",
    "lylanar and turlassil",
    "turlassil and lylanar",
    "lylanar & turlassil",
    "turlassil & lylanar",
}


def _paired_summaries(
    rows: tuple[BossGuideEncounterSummary, ...],
) -> tuple[BossGuideEncounterSummary, ...]:
    members = {
        row.encounter_id: row
        for row in rows
        if row.content_id == PAIR_CONTENT_ID and row.encounter_id in PAIR_MEMBERS
    }
    if set(members) != set(PAIR_MEMBERS):
        return rows

    first = members[PAIR_MEMBERS[0]]
    second = members[PAIR_MEMBERS[1]]
    location = first.location if first.location == second.location else (first.location or second.location)
    combined = BossGuideEncounterSummary(
        encounter_id=PAIR_ID,
        content_id=PAIR_CONTENT_ID,
        content_name=first.content_name or second.content_name,
        name=PAIR_NAME,
        location=location,
    )
    kept = [
        row
        for row in rows
        if not (row.content_id == PAIR_CONTENT_ID and row.encounter_id in PAIR_MEMBERS)
    ]
    kept.append(combined)
    return tuple(
        sorted(
            kept,
            key=lambda row: (
                row.content_name.casefold(),
                row.name.casefold(),
                row.encounter_id,
            ),
        )
    )


def _joined_distinct(values, separator: str = " / ") -> str:
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return separator.join(result)


def _combined_health(guides: tuple[EncounterBossGuide, ...]) -> tuple[tuple[str, str], ...]:
    rows = []
    for difficulty in ("normal", "veteran", "hardmode"):
        values = []
        for guide in guides:
            value = dict(guide.health).get(difficulty, "")
            if value:
                values.append(f"{guide.name}: {value}")
        if values:
            rows.append((difficulty, " | ".join(values)))
    return tuple(rows)


def _merge_pair_guides(guides: tuple[EncounterBossGuide, ...]) -> EncounterBossGuide:
    if len(guides) != 2:
        raise ValueError("Lylanar/Turlassil pairing requires exactly two member guides")
    first, second = guides
    if {first.encounter_id, second.encounter_id} != set(PAIR_MEMBERS):
        raise ValueError("Unexpected members for Lylanar/Turlassil paired encounter")

    ordered = tuple(
        next(guide for guide in guides if guide.encounter_id == member)
        for member in PAIR_MEMBERS
    )

    abilities = tuple(
        replace(ability, name=f"{guide.name} • {ability.name}")
        for guide in ordered
        for ability in guide.abilities
    )
    structural_phases = tuple(
        replace(
            phase,
            label=(f"{guide.name} • {phase.label}" if phase.label else guide.name),
        )
        for guide in ordered
        for phase in guide.structural_phases
    )
    timeline_facts = tuple(
        fact
        for guide in ordered
        for fact in guide.timeline_facts
    )
    phases = tuple(
        replace(
            phase,
            label=(f"{guide.name} • {phase.label}" if phase.label else guide.name),
        )
        for guide in ordered
        for phase in guide.phases
    )

    summary_parts = [
        f"{guide.name}: {guide.summary}"
        for guide in ordered
        if guide.summary
    ]

    return EncounterBossGuide(
        encounter_id=PAIR_ID,
        content_id=PAIR_CONTENT_ID,
        content_name=first.content_name or second.content_name,
        name=PAIR_NAME,
        summary="\n\n".join(summary_parts),
        location=_joined_distinct(guide.location for guide in ordered),
        species=_joined_distinct(guide.species for guide in ordered),
        reaction=_joined_distinct(guide.reaction for guide in ordered),
        health_record_present=any(guide.health_record_present for guide in ordered),
        health=_combined_health(ordered),
        abilities=abilities,
        phases=phases,
        structural_phases=structural_phases,
        timeline_facts=timeline_facts,
        source_url="",
        source_page_title=PAIR_NAME,
        source_revision_id=_joined_distinct(
            (guide.source_revision_id for guide in ordered),
            separator=" + ",
        ),
        retrieved_at=_joined_distinct(guide.retrieved_at for guide in ordered),
        source_license=_joined_distinct(guide.source_license for guide in ordered),
    )


def _configure_ability_table(self) -> None:
    """Keep wrapped ability descriptions readable even in a narrow split pane."""
    table = getattr(self, "abilities_table", None)
    if table is None:
        return

    table.setWordWrap(True)
    table.setTextElideMode(Qt.TextElideMode.ElideNone)

    header = table.horizontalHeader()
    header.setMinimumSectionSize(70)
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    # Stretch made Description absorb all remaining pressure from the timeline
    # pane, which could collapse it to a few characters. Give it a real width
    # and let the table use horizontal scrolling when the page is tighter.
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)

    table.setColumnWidth(0, 230)
    table.setColumnWidth(2, 380)
    table.setColumnWidth(3, 145)
    table.setColumnWidth(5, 120)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.resizeRowsToContents()


def _map_tab(self) -> QWidget:
    tab = QWidget()
    root = QVBoxLayout(tab)
    root.setContentsMargins(8, 8, 8, 8)
    root.setSpacing(8)

    toolbar = QHBoxLayout()
    toolbar.setSpacing(6)
    toolbar.addWidget(QLabel("RAID MAP"))

    self.raid_map_selector = QComboBox()
    self.raid_map_selector.setMinimumWidth(260)
    self.raid_map_selector.currentIndexChanged.connect(
        lambda _index: _render_selected_map(self)
    )
    toolbar.addWidget(self.raid_map_selector, 1)

    self.add_raid_map_button = QPushButton("Add Raid Map")
    self.add_raid_map_button.setToolTip(
        "Save a PNG, JPG, JPEG, or WebP Raid Map to the selected boss."
    )
    self.add_raid_map_button.clicked.connect(lambda: _add_raid_map(self))
    toolbar.addWidget(self.add_raid_map_button)

    self.remove_raid_map_button = QPushButton("Remove Map")
    self.remove_raid_map_button.clicked.connect(lambda: _remove_raid_map(self))
    toolbar.addWidget(self.remove_raid_map_button)
    root.addLayout(toolbar)

    self.raid_map_preview = QLabel("No Raid Maps saved for this boss.")
    self.raid_map_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.raid_map_preview.setWordWrap(True)
    self.raid_map_preview.setMinimumHeight(430)
    self.raid_map_preview.setProperty("bossArtworkPlaceholder", True)
    root.addWidget(self.raid_map_preview, 1)
    return tab


def _selected_encounter_id(self) -> str:
    if not hasattr(self, "boss_combo"):
        return ""
    return str(self.boss_combo.currentData() or "").strip()


def _refresh_map_list(self, preferred_map_id: str = "") -> None:
    if not hasattr(self, "raid_map_selector"):
        return
    encounter_id = _selected_encounter_id(self)
    self.raid_map_selector.blockSignals(True)
    self.raid_map_selector.clear()
    maps = ()
    if encounter_id:
        maps = self._boss_raid_map_store.list_maps(encounter_id)
        for row in maps:
            self.raid_map_selector.addItem(row.label, row.map_id)
    self.raid_map_selector.blockSignals(False)

    if preferred_map_id:
        index = self.raid_map_selector.findData(preferred_map_id)
        if index >= 0:
            self.raid_map_selector.setCurrentIndex(index)
    if self.raid_map_selector.count() > 0 and self.raid_map_selector.currentIndex() < 0:
        self.raid_map_selector.setCurrentIndex(0)

    self.add_raid_map_button.setEnabled(bool(encounter_id))
    self.remove_raid_map_button.setEnabled(bool(encounter_id and maps))
    _render_selected_map(self)


def _render_selected_map(self) -> None:
    if not hasattr(self, "raid_map_preview"):
        return
    encounter_id = _selected_encounter_id(self)
    map_id = str(self.raid_map_selector.currentData() or "").strip()
    record = next(
        (
            row
            for row in self._boss_raid_map_store.list_maps(encounter_id)
            if row.map_id == map_id
        ),
        None,
    ) if encounter_id and map_id else None
    if record is None:
        self.raid_map_preview.setPixmap(QPixmap())
        self.raid_map_preview.setText(
            "No Raid Maps saved for this boss.\nUse Add Raid Map to attach a positioning or strategy image."
            if encounter_id
            else "Select a boss to view its Raid Maps."
        )
        return

    path = self._boss_raid_map_store.resolve_path(record)
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        self.raid_map_preview.setPixmap(QPixmap())
        self.raid_map_preview.setText(f"Raid Map file is missing or unreadable:\n{path}")
        return

    target = self.raid_map_preview.size()
    if target.width() < 200 or target.height() < 200:
        target = QSize(1000, 560)
    self.raid_map_preview.setText("")
    self.raid_map_preview.setPixmap(
        pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


def _add_raid_map(self) -> None:
    encounter_id = _selected_encounter_id(self)
    if not encounter_id:
        return
    filename, _ = QFileDialog.getOpenFileName(
        self,
        "Add Raid Map to Boss",
        "",
        "Raid Map Images (*.png *.jpg *.jpeg *.webp);;All Files (*)",
    )
    if not filename:
        return
    try:
        record = self._boss_raid_map_store.import_map(encounter_id, filename)
    except (OSError, RuntimeError, ValueError) as exc:
        QMessageBox.warning(self, "Raid Map Not Saved", str(exc))
        return
    _refresh_map_list(self, record.map_id)
    if hasattr(self, "status"):
        self.status.success(f"Saved Raid Map to {self.boss_combo.currentText()}.")


def _remove_raid_map(self) -> None:
    encounter_id = _selected_encounter_id(self)
    map_id = str(self.raid_map_selector.currentData() or "").strip()
    if not encounter_id or not map_id:
        return
    label = self.raid_map_selector.currentText() or "this Raid Map"
    answer = QMessageBox.question(
        self,
        "Remove Raid Map",
        f"Remove {label!r} from this boss?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return
    self._boss_raid_map_store.remove_map(encounter_id, map_id)
    _refresh_map_list(self)


def install() -> None:
    """Install paired-boss presentation and the Mechanics Raid Map tab."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.mechanics_page import MechanicsPage

    original_summaries = EncounterBossGuideService.encounter_summaries
    original_get = EncounterBossGuideService.get
    original_page_init = MechanicsPage.__init__
    original_boss_changed = MechanicsPage._boss_changed
    original_refresh_context = MechanicsPage.refresh_context

    def summaries_with_pairs(service):
        return _paired_summaries(original_summaries(service))

    def get_with_pairs(service, encounter_id: str):
        if str(encounter_id or "").strip() != PAIR_ID:
            return original_get(service, encounter_id)
        guides = tuple(original_get(service, member) for member in PAIR_MEMBERS)
        return _merge_pair_guides(guides)

    def init_with_maps(self, *args, **kwargs):
        self._boss_raid_map_store = EncounterRaidMapStore(get_data_dir())
        original_page_init(self, *args, **kwargs)

        _configure_ability_table(self)

        for index in range(self.tabs.count()):
            if self.tabs.tabText(index).strip().upper() != "NOTES":
                continue
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, _map_tab(self), "MAP")
            break
        _refresh_map_list(self)

    def boss_changed_with_maps(self, index: int) -> None:
        original_boss_changed(self, index)
        _refresh_map_list(self)

    def refresh_context_with_pairs(self) -> None:
        original_refresh_context(self)
        objective = str(self.expedition.expedition.Objective or "").strip().casefold()
        if objective not in PAIR_OBJECTIVE_ALIASES or self.guide_service is None:
            return
        content_index = self.trial_combo.findData(PAIR_CONTENT_ID)
        if content_index >= 0:
            self.trial_combo.setCurrentIndex(content_index)
        self._populate_boss_combo(PAIR_ID)

    EncounterBossGuideService.encounter_summaries = summaries_with_pairs
    EncounterBossGuideService.get = get_with_pairs
    MechanicsPage.__init__ = init_with_maps
    MechanicsPage._boss_changed = boss_changed_with_maps
    MechanicsPage.refresh_context = refresh_context_with_pairs
    _INSTALLED = True
