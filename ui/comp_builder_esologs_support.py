from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea

from services.esologs_composition_evidence import (
    EsoLogsCompositionEvidence,
    EsoLogsCompositionEvidenceService,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _card(page, title: str) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == title:
            return card
    return None


def _current_trial(page) -> str:
    from ui.comp_builder_page import GOAL_TRIALS

    goal = page.goal_combo.currentText().strip()
    return GOAL_TRIALS.get(goal, "Custom Trial")


def _format_count_rows(rows: tuple[tuple[str, int], ...], *, limit: int = 3) -> str:
    if not rows:
        return "None observed"
    return ", ".join(f"{name} ×{count}" for name, count in rows[:limit])


def _format_observed_evidence(evidence: EsoLogsCompositionEvidence | None) -> str:
    if evidence is None:
        return "ESO LOGS OBSERVED EVIDENCE\nNo imported evidence for this trial yet."

    lines = [
        "ESO LOGS OBSERVED EVIDENCE",
        f"{evidence.sample_count} ranked team snapshot(s)",
    ]
    if evidence.encounter_names:
        lines.append("Encounters: " + ", ".join(evidence.encounter_names))
    lines.append("")

    for slot in evidence.slots:
        preferred = slot.preferred_class or "Unresolved class"
        confidence = round(slot.confidence * 100)
        alternatives = ", ".join(slot.alternative_classes) or "None observed"
        lines.extend(
            (
                f"{slot.slot_name}: {preferred} ({confidence}% of sampled chair observations)",
                f"  Alternatives: {alternatives}",
                f"  Gear: {_format_count_rows(slot.observed_gear_sets)}",
                f"  Abilities: {_format_count_rows(slot.observed_abilities)}",
            )
        )
    return "\n".join(lines)


def _append_report_provenance(page, evidence: EsoLogsCompositionEvidence) -> None:
    current = page.evidence_text.toPlainText().strip()
    marker = "ESO LOGS OBSERVED SNAPSHOTS"
    if marker in current:
        current = current.split(marker, 1)[0].rstrip()

    block = [
        marker,
        f"Trial: {evidence.trial_name or 'Unresolved'}",
        f"Samples: {evidence.sample_count}",
    ]
    if evidence.report_fights:
        block.append("Report/fight refs: " + ", ".join(evidence.report_fights))
    block.append(
        "Boundary: observed ranked-team evidence only; this does not prove an optimal class, provider, or build."
    )
    combined = "\n\n".join(part for part in (current, "\n".join(block)) if part)
    page.evidence_text.setPlainText(combined)


def _refresh_for_trial(page) -> None:
    results = getattr(page, "_esologs_loaded_results", ())
    trial = _current_trial(page)
    filtered = tuple(
        result
        for result in results
        if result.TrialName.strip().casefold() == trial.casefold()
    )

    if filtered:
        evidence = page._esologs_evidence_service.aggregate(filtered, trial_name=trial)
    else:
        evidence = None

    page._esologs_observed_evidence = evidence
    page.esologs_evidence_label.setText(_format_observed_evidence(evidence))
    page.apply_esologs_button.setEnabled(evidence is not None)

    if evidence is not None:
        _append_report_provenance(page, evidence)


def _load_esologs_evidence(page) -> None:
    filename, _filter = QFileDialog.getOpenFileName(
        page,
        "Load ESO Logs Top-Team Evidence",
        str(Path.cwd()),
        "JSON files (*.json);;All files (*.*)",
    )
    if not filename:
        return

    try:
        results = page._esologs_evidence_service.load_snapshots(filename)
    except (OSError, ValueError) as exc:
        page.status.error(f"Could not load ESO Logs evidence: {exc}")
        return

    if not results:
        page.status.warning("That file contains no usable top-team snapshots.")
        return

    page._esologs_loaded_results = results
    _refresh_for_trial(page)

    matching = sum(
        1
        for result in results
        if result.TrialName.strip().casefold() == _current_trial(page).casefold()
    )
    if matching:
        page.status.success(
            f"Loaded {matching} observed ESO Logs team snapshot(s) for {_current_trial(page)}."
        )
    else:
        page.status.info(
            f"Loaded {len(results)} ESO Logs snapshot(s), but none match {_current_trial(page)}."
        )


def _apply_esologs_classes(page) -> None:
    evidence = getattr(page, "_esologs_observed_evidence", None)
    if evidence is None:
        page.status.warning("Load matching ESO Logs evidence before applying observed classes.")
        return

    applied = 0
    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0)
        observed = evidence.slot(slot_name)
        if observed is None or not observed.preferred_class:
            continue

        selector = page.matrix_table.cellWidget(row, 2)
        if selector is None:
            continue
        index = selector.findText(observed.preferred_class)
        if index < 0:
            continue
        selector.setCurrentIndex(index)

        alternatives = page.matrix_table.item(row, 3)
        if alternatives is not None:
            alternatives.setText(
                ", ".join(observed.alternative_classes) or "No observed alternative"
            )
        applied += 1

    page.status.success(
        f"Applied observed ESO Logs class evidence to {applied} composition chair(s). "
        "Responsibilities, providers, and mechanic jobs were preserved."
    )


def _install_comp_esologs_ui(page) -> None:
    page._esologs_evidence_service = EsoLogsCompositionEvidenceService()
    page._esologs_loaded_results = ()
    page._esologs_observed_evidence = None

    actions = _card(page, "Actions")
    if actions is not None:
        row = QHBoxLayout()
        page.load_esologs_button = QPushButton("Load ESO Logs")
        page.apply_esologs_button = QPushButton("Apply ESO Logs Classes")
        page.apply_esologs_button.setEnabled(False)
        row.addWidget(page.load_esologs_button, 1)
        row.addWidget(page.apply_esologs_button, 1)
        actions.addLayout(row)
        page.load_esologs_button.clicked.connect(lambda *_: _load_esologs_evidence(page))
        page.apply_esologs_button.clicked.connect(lambda *_: _apply_esologs_classes(page))

    details = _card(page, "Composition Details & Summary")
    page.esologs_evidence_label = QLabel(_format_observed_evidence(None))
    page.esologs_evidence_label.setWordWrap(True)
    if details is not None:
        scroll = next(iter(details.findChildren(QScrollArea)), None)
        body = scroll.widget() if scroll is not None else None
        layout = body.layout() if body is not None else None
        if layout is not None:
            index = max(0, layout.count() - 1)
            layout.insertWidget(index, page.esologs_evidence_label)
        else:
            details.addWidget(page.esologs_evidence_label)

    page.goal_combo.currentTextChanged.connect(lambda *_: _refresh_for_trial(page))


def _comp_init_with_esologs(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_comp_esologs_ui(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_esologs
    _INSTALLED = True
