from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QScrollArea

from engine.config import get_data_dir
from services.comp_builder_build_candidates import (
    CompBuildCandidate,
    CompBuilderBuildCandidateService,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_RENDER_SLOTS = None


def _details_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Composition Details & Summary":
            return card
    return None


def _selected_row(page) -> int:
    row = page.matrix_table.currentRow()
    if row >= 0:
        return row
    return 0 if page.matrix_table.rowCount() else -1


def _source_label(candidate: CompBuildCandidate) -> str:
    if candidate.source_kind == "saved_build":
        return f"Saved BFF build • {candidate.source_name}"
    return f"Reference template • {candidate.source_name}"


def _compact(values: tuple[str, ...], *, limit: int = 8) -> str:
    if not values:
        return "None supplied by this source"
    shown = list(values[:limit])
    if len(values) > limit:
        shown.append(f"+{len(values) - limit} more")
    return " • ".join(shown)


def _candidate_text(candidate: CompBuildCandidate, rank: int) -> list[str]:
    lines = [
        f"#{rank}  {candidate.name}",
        f"Source: {_source_label(candidate)}",
        f"Class / Role: {candidate.eso_class or 'Unresolved'} / {candidate.role or 'Unresolved'}",
        f"Relevance: {candidate.score:.1f}",
        "Gear: " + _compact(candidate.gear_sets),
        "Skills: " + _compact(candidate.skills, limit=12),
    ]
    if candidate.mundus:
        lines.append(f"Mundus: {candidate.mundus}")
    if candidate.score_reasons:
        lines.append("Why it surfaced: " + " • ".join(candidate.score_reasons))
    if candidate.source_url:
        lines.append("Reference: " + candidate.source_url)
    if not candidate.complete_build:
        lines.append("Status: partial evidence, not a complete prescribed build")
    if candidate.unresolved:
        lines.append("Unresolved: " + " • ".join(candidate.unresolved[:3]))
    return lines


def _format_candidates(page) -> str:
    row = _selected_row(page)
    if row < 0:
        return "BUILD CANDIDATES • MERGED SOURCES\nNo composition chair selected."

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    role = page._cell_text(row, 1)
    preferred_class = page._selected_class(row) or "Any class"
    goal = page.goal_combo.currentText().strip()

    evidence = getattr(page, "_esologs_observed_evidence", None)
    observed = evidence.slot(slot_name) if evidence is not None else None
    observed_gear = (
        tuple(name for name, _count in observed.observed_gear_sets)
        if observed is not None
        else ()
    )
    observed_skills = (
        tuple(name for name, _count in observed.observed_abilities)
        if observed is not None
        else ()
    )

    try:
        candidates = page._comp_build_candidate_service.candidates_for_chair(
            goal=goal,
            slot_name=slot_name,
            role=role,
            preferred_class=preferred_class,
            observed_gear_sets=observed_gear,
            observed_skills=observed_skills,
        )
    except (OSError, ValueError) as exc:
        return (
            "BUILD CANDIDATES • MERGED SOURCES\n"
            f"Could not read candidate sources: {exc}"
        )

    lines = [
        "BUILD CANDIDATES • MERGED SOURCES",
        f"{slot_name} • {preferred_class} • {role}",
        "Saved builds and versioned references are ranked for relevance. This is not yet combat optimization.",
        "",
    ]
    if not candidates:
        lines.extend(
            (
                "No matching saved build or versioned reference template was found.",
                "ESO Logs evidence can remain useful even when players hide their complete setup.",
            )
        )
        return "\n".join(lines)

    for index, candidate in enumerate(candidates[:4], start=1):
        lines.extend(_candidate_text(candidate, index))
        if index < min(4, len(candidates)):
            lines.append("")
    return "\n".join(lines)


def _refresh_candidates(page) -> None:
    label = getattr(page, "comp_build_candidates_label", None)
    if label is not None:
        label.setText(_format_candidates(page))


def _wire_class_selectors(page) -> None:
    for row in range(page.matrix_table.rowCount()):
        selector = page.matrix_table.cellWidget(row, 2)
        if not isinstance(selector, QComboBox):
            continue
        if selector.property("compCandidateRefreshConnected"):
            continue
        selector.currentTextChanged.connect(lambda *_: _refresh_candidates(page))
        selector.setProperty("compCandidateRefreshConnected", True)


def _install_candidate_ui(page) -> None:
    page._comp_build_candidate_service = CompBuilderBuildCandidateService(get_data_dir())
    page.comp_build_candidates_label = QLabel()
    page.comp_build_candidates_label.setWordWrap(True)

    details = _details_card(page)
    if details is not None:
        scroll = next(iter(details.findChildren(QScrollArea)), None)
        body = scroll.widget() if scroll is not None else None
        layout = body.layout() if body is not None else None
        if layout is not None:
            selected = getattr(page, "esologs_selected_chair_label", None)
            selected_index = layout.indexOf(selected) if selected is not None else -1
            insert_at = selected_index + 1 if selected_index >= 0 else min(3, layout.count())
            layout.insertWidget(insert_at, page.comp_build_candidates_label)
        else:
            details.addWidget(page.comp_build_candidates_label)

    page.matrix_table.currentCellChanged.connect(lambda *_: _refresh_candidates(page))
    page.goal_combo.currentTextChanged.connect(lambda *_: _refresh_candidates(page))
    if hasattr(page, "refresh_esologs_button"):
        page.refresh_esologs_button.clicked.connect(lambda *_: _refresh_candidates(page))
    if hasattr(page, "apply_esologs_button"):
        page.apply_esologs_button.clicked.connect(lambda *_: _refresh_candidates(page))

    _wire_class_selectors(page)
    _refresh_candidates(page)


def _comp_init_with_build_candidates(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_candidate_ui(self)


def _render_slots_with_candidate_refresh(self, slots) -> None:
    assert _ORIGINAL_RENDER_SLOTS is not None
    _ORIGINAL_RENDER_SLOTS(self, slots)
    if hasattr(self, "_comp_build_candidate_service"):
        _wire_class_selectors(self)
        _refresh_candidates(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT, _ORIGINAL_RENDER_SLOTS
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_RENDER_SLOTS = CompBuilderPage._render_slots
    CompBuilderPage.__init__ = _comp_init_with_build_candidates
    CompBuilderPage._render_slots = _render_slots_with_candidate_refresh
    _INSTALLED = True
