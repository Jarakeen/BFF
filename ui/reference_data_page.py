from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.reference_common_names import enrich_reference_entries_with_common_names
from ui.reference_data_model import ReferenceEntry, build_reference_entries, entry_types, source_scopes
from ui.reference_encounter_evidence import enrich_reference_entries_with_encounter_evidence
from ui.reference_mitigations import enrich_reference_entries_with_mitigations
from ui.reference_named_effects import build_named_effect_reference_entries
from ui.reference_provider_relationships import load_and_enrich_reference_entries


def _reference_details_html(details) -> str:
    """Render Reference detail labels with a strong visual anchor."""

    rows = []
    for label, value in details:
        safe_label = escape(str(label or ""))
        safe_value = escape(str(value or "")).replace("\n", "<br>")
        rows.append(f"<b>{safe_label}:</b> {safe_value}")
    return "<br>".join(rows)


def _first_detail(entry: ReferenceEntry, *needles: str) -> str:
    """Return the first useful detail matching requested concepts.

    Reviewed evidence often stores multiple structured facts in one semicolon-
    delimited value. Match those individual segments before falling back to the
    whole value when the label itself describes the requested concept.
    """

    wanted = tuple(value.casefold() for value in needles)
    for label, value in entry.details:
        label_text = str(label or "").casefold()
        value_text = str(value or "").strip()
        if not value_text:
            continue

        segments = tuple(part.strip() for part in value_text.split(";") if part.strip())
        for segment in segments:
            segment_text = segment.casefold()
            if any(needle in segment_text for needle in wanted):
                if segment_text not in {"yes", "no", "unknown", "not modeled"}:
                    return segment

        if any(needle in label_text for needle in wanted):
            if value_text.casefold() in {"yes", "no", "unknown", "not modeled"}:
                continue
            return value_text
    return ""


def _encounter_name(entry: ReferenceEntry) -> str:
    for label, value in entry.details:
        if str(label).casefold() == "encounter" and str(value).strip():
            return str(value).strip()
    if " — " in entry.name:
        return entry.name.rsplit(" — ", 1)[1].strip()
    return ""


def _raid_lead_snapshot_rows(entry: ReferenceEntry) -> tuple[tuple[str, str], ...]:
    """Project the most useful mechanic facts for fast raid-lead scanning.

    This is presentation only. Values come from the already assembled canonical /
    reviewed Reference entry and are never invented when the source data is absent.
    """

    if entry.entry_type not in {"Mechanic", "Mechanic Evidence"}:
        return ()

    what = _first_detail(
        entry,
        "core behavior",
        "veteran behavior",
        "behavior",
        "damage pattern",
        "handling",
        "reviewed details",
    )
    timing = _first_detail(entry, "duration", "detonation", "timing", "window", "cadence")
    size = _first_detail(entry, "radius", "range", "size", "distance", "meters", "metres")
    targets = _first_detail(entry, "target count", "targeting", "target pattern", "targets")
    kill_risk = _first_detail(entry, "failure severity", "fatal", "wipe", "kill")
    source = _encounter_name(entry)

    rows = [
        ("What it does", what or entry.summary),
        ("Duration / timing", timing or "No reviewed timing value yet."),
        ("Size / radius", size or "No reviewed size or radius yet."),
        ("Targets / kill risk", targets or kill_risk or "No reviewed target or kill-risk value yet."),
        ("Comes from", source or "Source encounter not recorded."),
    ]
    if entry.mitigation_note:
        rows.append(("How to mitigate", entry.mitigation_note))
    return tuple(rows)


def _raid_lead_snapshot_html(entry: ReferenceEntry) -> str:
    rows = _raid_lead_snapshot_rows(entry)
    if not rows:
        return ""
    body = "<br>".join(
        f"<b>{escape(label)}:</b> {escape(value)}"
        for label, value in rows
    )
    return f"<b>RAID LEAD SNAPSHOT</b><br>{body}"


class ReferenceDataPage(FoundryPage):
    """Human-readable window into BFF combat knowledge and gameplay practice."""

    def __init__(self, parent=None):
        super().__init__(parent)
        base_entries = (
            *build_reference_entries(
                include_encounters=True,
                include_effects=True,
            ),
            *build_named_effect_reference_entries(),
        )
        base_entries = enrich_reference_entries_with_encounter_evidence(base_entries)
        entries = load_and_enrich_reference_entries(base_entries)
        entries = enrich_reference_entries_with_common_names(entries)
        entries = enrich_reference_entries_with_mitigations(entries)
        self._entries = {entry.name: entry for entry in entries}
        self._build_ui()
        self._load_list()
        if self.results.count():
            self.results.setCurrentRow(0)

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Combat Reference",
            subtitle=(
                "Search mechanics, combat rules, roles, effects, and gameplay practice. "
                "See what BFF knows, what the mechanic does, and how to survive it."
            ),
            department="Raid Engine • Reference",
        )
        self.set_header(self.header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search mechanics, rules, roles, effects, or terminology...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._load_list)
        self.header.add_context_widget(self._context_field("SEARCH", self.search))

        self.source_filter = QComboBox()
        self.source_filter.addItem("All Sources")
        self.source_filter.addItems(source_scopes(self._entries.values()))
        self.source_filter.currentTextChanged.connect(self._load_list)
        self.header.add_context_widget(self._context_field("SOURCE", self.source_filter))

        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        self.type_filter.addItems(entry_types(self._entries.values()))
        self.type_filter.currentTextChanged.connect(self._load_list)
        self.header.add_context_widget(self._context_field("ENTRY TYPE", self.type_filter))

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(8)

        index_card = FoundryCard("Reference Index", "⌕").set_watermark("compass", 0.04)
        self.results = QListWidget()
        self.results.currentTextChanged.connect(self._show_entry)
        index_card.addWidget(self.results)
        workspace.addWidget(index_card, 1)

        center = QVBoxLayout()
        center.setSpacing(8)

        self.entry_card = FoundryCard("Reference Entry", "✦").set_watermark("compass", 0.055)
        self.entry_name = QLabel()
        self.entry_name.setProperty("heroTitle", True)
        self.raid_lead_snapshot = QLabel()
        self.raid_lead_snapshot.setWordWrap(True)
        self.raid_lead_snapshot.setTextFormat(Qt.TextFormat.RichText)
        snapshot_font = self.raid_lead_snapshot.font()
        snapshot_font.setPointSize(max(11, snapshot_font.pointSize() + 1))
        self.raid_lead_snapshot.setFont(snapshot_font)
        self.entry_summary = QLabel()
        self.entry_summary.setWordWrap(True)
        self.entry_details = QLabel()
        self.entry_details.setWordWrap(True)
        self.entry_details.setTextFormat(Qt.TextFormat.RichText)
        self.entry_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.entry_card.addWidget(self.entry_name)
        self.entry_card.addWidget(self.raid_lead_snapshot)
        self.entry_card.addWidget(self.entry_summary)
        self.entry_card.addWidget(self.entry_details)
        self.entry_card.addStretch(1)
        center.addWidget(self.entry_card, 4)

        related = FoundryCard("Related / Appears In", "↗").set_watermark("compass", 0.035)
        self.related_label = QLabel()
        self.related_label.setWordWrap(True)
        related.addWidget(self.related_label)
        center.addWidget(related, 1)

        evidence = FoundryCard("Evidence / Provenance", "⌁").set_watermark("compass", 0.035)
        self.evidence_label = QLabel()
        self.evidence_label.setWordWrap(True)
        self.evidence_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        evidence.addWidget(self.evidence_label)
        center.addWidget(evidence, 1)

        workspace.addLayout(center, 3)

        right = QVBoxLayout()
        right.setSpacing(8)

        death = FoundryCard("Why Did We Die?", "☠").make_parchment().set_watermark("compass", 0.10)
        self.death_label = QLabel()
        self.death_label.setWordWrap(True)
        death.addWidget(self.death_label)
        self.death_button = QPushButton("Analyze Selected Death")
        self.death_button.setToolTip(
            "Death-log analysis wiring is planned; this entry currently shows reference guidance."
        )
        death.addWidget(self.death_button)
        right.addWidget(death, 2)

        image = FoundryCard("Mechanic Visual", "◉").set_watermark("compass", 0.06)
        self.visual = QLabel(
            "MECHANIC / ATTACK VISUAL\n\n"
            "Artwork, icon, combat-log sample,\n"
            "or positioning diagram can live here."
        )
        self.visual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visual.setMinimumHeight(260)
        self.visual.setProperty("bossArtworkPlaceholder", True)
        image.addWidget(self.visual)
        right.addWidget(image, 2)

        mitigation = FoundryCard("How to Mitigate", "✚").make_parchment().set_watermark("feather", 0.12)
        self.mitigation_label = QLabel()
        self.mitigation_label.setWordWrap(True)
        mitigation_font = self.mitigation_label.font()
        mitigation_font.setPointSize(max(13, mitigation_font.pointSize() + 3))
        mitigation_font.setBold(True)
        self.mitigation_label.setFont(mitigation_font)
        mitigation.addWidget(self.mitigation_label)
        right.addWidget(mitigation, 2)

        used_by = FoundryCard("Used By FoundryDock", "⚙").set_watermark("compass", 0.04)
        self.used_by_label = QLabel()
        self.used_by_label.setWordWrap(True)
        used_by.addWidget(self.used_by_label)
        right.addWidget(used_by, 1)

        workspace.addLayout(right, 2)

        host = QWidget()
        host.setLayout(workspace)
        self.add_workspace(host)

        self.status = FoundryStatusBar()
        self.set_status(self.status)
        self.status.info(
            f"Combat Reference ready • {len(self._entries)} entries loaded from canonical encounter/effect, reviewed encounter evidence, named-effect, reviewed provider, shared gameplay-practice, player-facing terminology, and mitigation data."
        )

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

    def _load_list(self, *_args):
        query = self.search.text().strip().casefold() if hasattr(self, "search") else ""
        source = self.source_filter.currentText() if hasattr(self, "source_filter") else "All Sources"
        entry_type = self.type_filter.currentText() if hasattr(self, "type_filter") else "All Types"
        current = (
            self.results.currentItem().text()
            if hasattr(self, "results") and self.results.currentItem()
            else ""
        )

        self.results.blockSignals(True)
        self.results.clear()
        for entry in self._entries.values():
            if query and query not in entry.search_text:
                continue
            if source != "All Sources" and entry.source_scope != source:
                continue
            if entry_type != "All Types" and entry.entry_type != entry_type:
                continue
            self.results.addItem(entry.name)
        self.results.blockSignals(False)

        matches = self.results.findItems(current, Qt.MatchFlag.MatchExactly)
        if matches:
            self.results.setCurrentItem(matches[0])
        elif self.results.count():
            self.results.setCurrentRow(0)
            self._show_entry(self.results.currentItem().text())
        else:
            self._clear_entry()

    def _clear_entry(self):
        self.entry_card.set_title("REFERENCE ENTRY")
        self.entry_name.setText("NO MATCHING ENTRY")
        self.raid_lead_snapshot.clear()
        self.raid_lead_snapshot.hide()
        self.entry_summary.setText("Adjust the search or filters.")
        self.entry_details.clear()
        self.related_label.setText("No related entries.")
        self.evidence_label.setText("No evidence for the current filter result.")
        self.death_label.setText("No death-analysis guidance for the current filter result.")
        self.mitigation_label.setText("No reviewed mitigation guidance for the current filter result.")
        self.used_by_label.setText("No consuming systems shown.")

    def _show_entry(self, name: str):
        entry = self._entries.get(name)
        if entry is None:
            return

        self.entry_card.set_title(" • ".join(entry.tags) or entry.entry_type.upper())
        self.entry_name.setText(entry.name.upper())
        snapshot = _raid_lead_snapshot_html(entry)
        self.raid_lead_snapshot.setVisible(bool(snapshot))
        self.raid_lead_snapshot.setText(snapshot)
        self.entry_summary.setText(entry.summary)
        self.entry_details.setText(_reference_details_html(entry.details))
        self.related_label.setText(
            "\n".join(f"• {value}" for value in entry.related)
            if entry.related
            else "No related entries registered."
        )
        self.evidence_label.setText(
            "\n".join(f"• {value}" for value in entry.evidence)
            if entry.evidence
            else "Evidence source not registered. Treat this entry as unresolved."
        )
        self.death_label.setText(entry.death_note or "No death-analysis guidance registered.")
        self.mitigation_label.setText(
            entry.mitigation_note or "No reviewed mitigation guidance registered yet."
        )
        self.used_by_label.setText(
            "\n".join(f"• {value}" for value in entry.used_by)
            if entry.used_by
            else "No consuming FoundryDock system registered."
        )
