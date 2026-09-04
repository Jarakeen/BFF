from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea

from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.esologs_composition_evidence import (
    EsoLogsCompositionEvidence,
    EsoLogsCompositionEvidenceService,
)
from services.settings_service import SettingsService
from services.top_team_service import TopTeamService
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


def _top_team_service() -> TopTeamService:
    settings = SettingsService(Path("settings.json")).load()
    return TopTeamService(
        EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )
    )


def _format_count_rows(rows: tuple[tuple[str, int], ...], *, limit: int = 3) -> str:
    if not rows:
        return "None observed"
    return ", ".join(f"{name} ×{count}" for name, count in rows[:limit])


def _format_count_lines(rows: tuple[tuple[str, int], ...], *, limit: int) -> str:
    if not rows:
        return "• None observed"
    return "\n".join(f"• {name} ×{count}" for name, count in rows[:limit])


def _format_observed_evidence(evidence: EsoLogsCompositionEvidence | None) -> str:
    if evidence is None:
        return "ESO LOGS OBSERVED EVIDENCE\nNo live evidence fetched for this trial yet."

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


def _selected_row(page) -> int:
    row = page.matrix_table.currentRow()
    if row >= 0:
        return row
    return 0 if page.matrix_table.rowCount() else -1


def _format_selected_chair(page) -> str:
    row = _selected_row(page)
    if row < 0:
        return "SELECTED CHAIR SETUP\nNo composition chair selected."

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    role = page._cell_text(row, 1) or "Unresolved role"
    planned_class = page._selected_class(row) or "Any class"
    required = page._cell_text(row, 4) or "None declared"
    optional = page._cell_text(row, 5) or "None declared"
    providers = page._cell_text(row, 6) or "None declared"
    mechanics = page._cell_text(row, 7) or "None declared"

    evidence = getattr(page, "_esologs_observed_evidence", None)
    observed = evidence.slot(slot_name) if evidence is not None else None

    lines = [
        "SELECTED CHAIR SETUP",
        f"{slot_name} • {role}",
        "",
        "PLANNED CHAIR",
        f"Class: {planned_class}",
        f"Required: {required}",
        f"Optional / Flex: {optional}",
        f"Providers: {providers}",
        f"Mechanic Jobs: {mechanics}",
        "",
        "OBSERVED SETUP • ESO LOGS",
    ]

    if observed is None:
        lines.extend(
            (
                "No live ranked-team evidence has been resolved for this chair yet.",
                "Use Refresh ESO Logs for the selected trial.",
            )
        )
    else:
        confidence = round(observed.confidence * 100)
        alternatives = ", ".join(observed.alternative_classes) or "None observed"
        lines.extend(
            (
                f"Class: {observed.preferred_class or 'Unresolved'} ({confidence}% of sampled chair observations)",
                f"Alternatives: {alternatives}",
                "",
                "Gear sets observed:",
                _format_count_lines(observed.observed_gear_sets, limit=10),
                "",
                "Skills / abilities observed:",
                _format_count_lines(observed.observed_abilities, limit=14),
            )
        )
        if evidence.encounter_names:
            lines.extend(("", "Encounters: " + ", ".join(evidence.encounter_names)))
        if evidence.report_fights:
            lines.append("Report/fight refs: " + ", ".join(evidence.report_fights))

    lines.extend(
        (
            "",
            "RECOMMENDED SETUP",
            "Gear: not prescribed yet from a sourced build recommendation.",
            "Skills: not prescribed yet from a sourced build recommendation.",
            "Observed ESO Logs usage is evidence, not automatically a recommendation.",
        )
    )
    return "\n".join(lines)


def _refresh_selected_chair(page) -> None:
    label = getattr(page, "esologs_selected_chair_label", None)
    if label is not None:
        label.setText(_format_selected_chair(page))


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


def _clear_esologs_evidence(page) -> None:
    page._esologs_observed_evidence = None
    page.esologs_evidence_label.setText(_format_observed_evidence(None))
    page.apply_esologs_button.setEnabled(False)
    _refresh_selected_chair(page)


def _refresh_live_esologs(page) -> None:
    trial_name = _current_trial(page)
    if trial_name == "Custom Trial":
        _clear_esologs_evidence(page)
        page.status.info("Choose a published trial goal before refreshing ESO Logs evidence.")
        return

    page.refresh_esologs_button.setEnabled(False)
    page.status.info(f"Fetching current top-ranked {trial_name} teams from ESO Logs...")

    try:
        service = _top_team_service()
        trials = service.list_trials()
        trial = next(
            (
                item
                for item in trials
                if str(item.get("name", "")).strip().casefold() == trial_name.casefold()
            ),
            None,
        )
        if trial is None:
            raise EsoLogsApiError(f"ESO Logs did not return the trial {trial_name!r}.")

        results = []
        failures: list[str] = []
        for encounter in trial.get("encounters") or ():
            try:
                results.append(
                    service.get_top_team(
                        zone_id=int(trial["id"]),
                        zone_name=str(trial["name"]),
                        encounter_id=int(encounter["id"]),
                        encounter_name=str(encounter["name"]),
                    )
                )
            except (EsoLogsApiError, KeyError, TypeError, ValueError) as exc:
                failures.append(f"{encounter.get('name', 'Unknown encounter')}: {exc}")

        if not results:
            detail = failures[0] if failures else "No ranked encounters returned usable team data."
            raise EsoLogsApiError(detail)

        evidence = page._esologs_evidence_service.aggregate(
            tuple(results),
            trial_name=trial_name,
        )
        page._esologs_observed_evidence = evidence
        page.esologs_evidence_label.setText(_format_observed_evidence(evidence))
        page.apply_esologs_button.setEnabled(True)
        _append_report_provenance(page, evidence)
        _refresh_selected_chair(page)

        if failures:
            page.status.warning(
                f"Loaded {len(results)} top-team encounter snapshot(s) for {trial_name}; "
                f"{len(failures)} encounter(s) could not be read."
            )
        else:
            page.status.success(
                f"Loaded {len(results)} live top-team encounter snapshot(s) for {trial_name}."
            )
    except EsoLogsApiError as exc:
        _clear_esologs_evidence(page)
        page.status.error(str(exc))
    except Exception as exc:
        _clear_esologs_evidence(page)
        page.status.error(f"ESO Logs refresh failed: {exc}")
    finally:
        page.refresh_esologs_button.setEnabled(True)


def _apply_esologs_classes(page) -> None:
    evidence = getattr(page, "_esologs_observed_evidence", None)
    if evidence is None:
        page.status.warning("Refresh matching ESO Logs evidence before applying observed classes.")
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

    _refresh_selected_chair(page)
    page.status.success(
        f"Applied observed ESO Logs class evidence to {applied} composition chair(s). "
        "Responsibilities, providers, and mechanic jobs were preserved."
    )


def _install_comp_esologs_ui(page) -> None:
    page._esologs_evidence_service = EsoLogsCompositionEvidenceService()
    page._esologs_observed_evidence = None

    actions = _card(page, "Actions")
    if actions is not None:
        row = QHBoxLayout()
        page.refresh_esologs_button = QPushButton("Refresh ESO Logs")
        page.apply_esologs_button = QPushButton("Apply Observed Classes")
        page.apply_esologs_button.setEnabled(False)
        row.addWidget(page.refresh_esologs_button, 1)
        row.addWidget(page.apply_esologs_button, 1)
        actions.addLayout(row)
        page.refresh_esologs_button.clicked.connect(lambda *_: _refresh_live_esologs(page))
        page.apply_esologs_button.clicked.connect(lambda *_: _apply_esologs_classes(page))

    details = _card(page, "Composition Details & Summary")
    page.esologs_evidence_label = QLabel(_format_observed_evidence(None))
    page.esologs_evidence_label.setWordWrap(True)
    page.esologs_selected_chair_label = QLabel(_format_selected_chair(page))
    page.esologs_selected_chair_label.setWordWrap(True)
    if details is not None:
        scroll = next(iter(details.findChildren(QScrollArea)), None)
        body = scroll.widget() if scroll is not None else None
        layout = body.layout() if body is not None else None
        if layout is not None:
            index = max(0, layout.count() - 1)
            layout.insertWidget(index, page.esologs_evidence_label)
            layout.insertWidget(index + 1, page.esologs_selected_chair_label)
        else:
            details.addWidget(page.esologs_evidence_label)
            details.addWidget(page.esologs_selected_chair_label)

    page.matrix_table.currentCellChanged.connect(
        lambda *_: _refresh_selected_chair(page)
    )
    page.goal_combo.currentTextChanged.connect(lambda *_: _clear_esologs_evidence(page))

    if page.matrix_table.rowCount() and page.matrix_table.currentRow() < 0:
        page.matrix_table.setCurrentCell(0, 0)
    _refresh_selected_chair(page)


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
