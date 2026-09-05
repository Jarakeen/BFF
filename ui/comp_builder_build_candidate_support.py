from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QScrollArea

from engine.config import get_data_dir
from services.comp_builder_build_candidates import (
    CompBuildCandidate,
    CompBuilderBuildCandidateService,
)
from services.generated_roster_plan_service import GeneratedRosterPlanSlot
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_RENDER_SLOTS = None
_ORIGINAL_SEND_TO_ROSTER = None


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


def _chair_candidates(page, row: int) -> tuple[CompBuildCandidate, ...]:
    if row < 0:
        return ()
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
    return page._comp_build_candidate_service.candidates_for_chair(
        goal=goal,
        slot_name=slot_name,
        role=role,
        preferred_class=preferred_class,
        observed_gear_sets=observed_gear,
        observed_skills=observed_skills,
    )


def _saved_player_key(candidate: CompBuildCandidate) -> str:
    if candidate.source_kind != "saved_build":
        return ""
    return str(candidate.source_name or "").strip().casefold()


def _first_unused_candidate(
    candidates: tuple[CompBuildCandidate, ...],
    used_saved_players: set[str],
) -> CompBuildCandidate | None:
    """Return the first ranked candidate that does not clone a saved player."""

    for candidate in candidates:
        player_key = _saved_player_key(candidate)
        if player_key and player_key in used_saved_players:
            continue
        return candidate
    return None


def _used_saved_players(page) -> set[str]:
    return {
        key
        for candidate in getattr(page, "_comp_applied_candidates", {}).values()
        if (key := _saved_player_key(candidate))
    }


def _format_candidates(page) -> str:
    row = _selected_row(page)
    if row < 0:
        return "BUILD CANDIDATES • MERGED SOURCES\nNo composition chair selected."

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    role = page._cell_text(row, 1)
    preferred_class = page._selected_class(row) or "Any class"
    try:
        candidates = _chair_candidates(page, row)
    except (OSError, ValueError) as exc:
        return (
            "BUILD CANDIDATES • MERGED SOURCES\n"
            f"Could not read candidate sources: {exc}"
        )

    lines = [
        "BUILD CANDIDATES • MERGED SOURCES",
        f"{slot_name} • {preferred_class} • {role}",
        "Saved builds and versioned references are ranked for relevance. This is not yet combat optimization.",
    ]
    applied = getattr(page, "_comp_applied_candidates", {}).get(slot_name)
    if applied is not None:
        lines.append(f"APPLIED TO CHAIR: {applied.name} • {_source_label(applied)}")
    lines.append("")

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
    button = getattr(page, "apply_comp_candidate_button", None)
    if button is not None:
        try:
            button.setEnabled(bool(_chair_candidates(page, _selected_row(page))))
        except (OSError, ValueError):
            button.setEnabled(False)
    all_button = getattr(page, "apply_all_comp_candidates_button", None)
    if all_button is not None:
        all_button.setEnabled(page.matrix_table.rowCount() > 0)


def _class_changed(page, row: int) -> None:
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    applied = getattr(page, "_comp_applied_candidates", {}).get(slot_name)
    if applied is not None:
        selected = page._selected_class(row)
        if (
            selected
            and selected.casefold() != "any class"
            and applied.eso_class
            and selected.casefold() != applied.eso_class.casefold()
        ):
            page._comp_applied_candidates.pop(slot_name, None)
    _refresh_candidates(page)


def _wire_class_selectors(page) -> None:
    for row in range(page.matrix_table.rowCount()):
        selector = page.matrix_table.cellWidget(row, 2)
        if not isinstance(selector, QComboBox):
            continue
        if selector.property("compCandidateRefreshConnected"):
            continue
        selector.currentTextChanged.connect(
            lambda *_args, row=row: _class_changed(page, row)
        )
        selector.setProperty("compCandidateRefreshConnected", True)


def _set_candidate_for_row(page, row: int, candidate: CompBuildCandidate) -> str:
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    page._comp_applied_candidates[slot_name] = candidate

    if candidate.eso_class:
        selector = page.matrix_table.cellWidget(row, 2)
        if isinstance(selector, QComboBox):
            index = selector.findText(candidate.eso_class)
            if index >= 0:
                selector.setCurrentIndex(index)
    return slot_name


def _apply_top_candidate(page, *_args) -> None:
    row = _selected_row(page)
    if row < 0:
        page.status.warning("Select a composition chair before applying a build candidate.")
        return
    try:
        candidates = _chair_candidates(page, row)
    except (OSError, ValueError) as exc:
        page.status.error(f"Could not read build candidates: {exc}")
        return
    if not candidates:
        page.status.warning("No matching build candidate is available for this chair.")
        return

    used_saved_players = _used_saved_players(page)
    current_slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    existing = page._comp_applied_candidates.get(current_slot)
    if existing is not None:
        existing_key = _saved_player_key(existing)
        if existing_key:
            used_saved_players.discard(existing_key)

    candidate = _first_unused_candidate(candidates, used_saved_players)
    if candidate is None:
        page.status.warning(
            "Matching candidates exist, but every saved-player option is already assigned "
            "to another composition chair."
        )
        return

    slot_name = _set_candidate_for_row(page, row, candidate)
    status = "complete build" if candidate.complete_build else "partial build evidence"
    page.status.success(
        f"Applied {candidate.name} to {slot_name} as {status}. "
        "Send to Roster will preserve this candidate evidence."
    )
    _refresh_candidates(page)


def _apply_best_candidates_to_all(page, *_args) -> None:
    """Fill unassigned chairs from ranked candidates without duplicating saved people."""

    if page.matrix_table.rowCount() <= 0:
        page.status.warning("There are no composition chairs to fill.")
        return

    used_saved_players = _used_saved_players(page)
    applied_count = 0
    skipped_existing = 0
    unresolved: list[str] = []

    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        if slot_name in page._comp_applied_candidates:
            skipped_existing += 1
            continue
        try:
            candidates = _chair_candidates(page, row)
        except (OSError, ValueError) as exc:
            unresolved.append(f"{slot_name}: {exc}")
            continue

        candidate = _first_unused_candidate(candidates, used_saved_players)
        if candidate is None:
            unresolved.append(f"{slot_name}: no unused matching candidate")
            continue

        _set_candidate_for_row(page, row, candidate)
        player_key = _saved_player_key(candidate)
        if player_key:
            used_saved_players.add(player_key)
        applied_count += 1

    _refresh_candidates(page)
    open_count = page.matrix_table.rowCount() - len(page._comp_applied_candidates)
    message = (
        f"Applied the best eligible candidate to {applied_count} chair(s); "
        f"preserved {skipped_existing} existing choice(s); {open_count} chair(s) remain open."
    )
    if unresolved:
        page.status.warning(message + " " + " • ".join(unresolved[:4]))
    else:
        page.status.success(message)


def _install_candidate_ui(page) -> None:
    page._comp_build_candidate_service = CompBuilderBuildCandidateService(get_data_dir())
    page._comp_applied_candidates: dict[str, CompBuildCandidate] = {}
    page.comp_build_candidates_label = QLabel()
    page.comp_build_candidates_label.setWordWrap(True)
    page.apply_comp_candidate_button = FoundryButton(
        "Apply Top Candidate",
        role=ButtonRole.PRIMARY,
        compact=True,
    )
    page.apply_comp_candidate_button.setEnabled(False)
    page.apply_comp_candidate_button.clicked.connect(
        lambda *_: _apply_top_candidate(page)
    )
    page.apply_all_comp_candidates_button = FoundryButton(
        "Apply Best to All Chairs",
        role=ButtonRole.SUCCESS,
        compact=True,
    )
    page.apply_all_comp_candidates_button.setEnabled(False)
    page.apply_all_comp_candidates_button.clicked.connect(
        lambda *_: _apply_best_candidates_to_all(page)
    )

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
            layout.insertWidget(insert_at + 1, page.apply_comp_candidate_button)
            layout.insertWidget(insert_at + 2, page.apply_all_comp_candidates_button)
        else:
            details.addWidget(page.comp_build_candidates_label)
            details.addWidget(page.apply_comp_candidate_button)
            details.addWidget(page.apply_all_comp_candidates_button)

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
    if hasattr(self, "_comp_applied_candidates"):
        self._comp_applied_candidates.clear()
        _wire_class_selectors(self)
        _refresh_candidates(self)


def _candidate_unresolved(candidate: CompBuildCandidate, base_detail: str) -> str:
    details = [base_detail, f"Candidate source: {_source_label(candidate)}."]
    if candidate.skills:
        details.append("Observed/known skills: " + ", ".join(candidate.skills) + ".")
    if candidate.mundus:
        details.append(f"Mundus: {candidate.mundus}.")
    if not candidate.complete_build:
        details.append("Candidate is partial evidence, not a complete prescribed build.")
    if candidate.unresolved:
        details.append("Unresolved: " + "; ".join(candidate.unresolved) + ".")
    return " ".join(details)


def _send_to_roster_with_candidates(self, *_args) -> None:
    applied = getattr(self, "_comp_applied_candidates", {})
    if not applied:
        assert _ORIGINAL_SEND_TO_ROSTER is not None
        _ORIGINAL_SEND_TO_ROSTER(self)
        return

    goal = self.goal_combo.currentText().strip() or "Custom Goal"
    plan_name = self.plan_name_input.text().strip() or f"{goal} Composition"
    slots: list[GeneratedRosterPlanSlot] = []
    for row in range(self.matrix_table.rowCount()):
        slot_name = self._cell_text(row, 0)
        selected_class = self._selected_class(row)
        alternatives = self._cell_text(row, 3) or "Flexible"
        required = self._cell_text(row, 4) or "Open responsibility"
        optional = self._cell_text(row, 5) or "None declared"
        providers = self._cell_text(row, 6) or "None declared"
        mechanic_jobs = self._cell_text(row, 7) or "None declared"
        detail = (
            f"Composition requirement. Alternatives: {alternatives}. "
            f"Required: {required}. Optional/flex: {optional}. "
            f"Providers: {providers}. Mechanic jobs: {mechanic_jobs}."
        )
        candidate = applied.get(slot_name)
        if candidate is None:
            concrete = selected_class != "Any class"
            slots.append(
                GeneratedRosterPlanSlot(
                    slot_name=slot_name,
                    kind="prescribed_recruit" if concrete else "open_recruit",
                    player_name="Recruitment Needed",
                    character_name="",
                    eso_class=selected_class,
                    build_name="Composition requirement",
                    gear_summary="",
                    unresolved=detail,
                )
            )
            continue

        is_saved = candidate.source_kind == "saved_build"
        slots.append(
            GeneratedRosterPlanSlot(
                slot_name=slot_name,
                kind="prescribed_player" if is_saved else "prescribed_recruit",
                player_name=candidate.source_name if is_saved else "Recruitment Needed",
                character_name=candidate.source_name if is_saved else "",
                eso_class=candidate.eso_class or selected_class,
                build_name=candidate.name,
                gear_summary=" + ".join(candidate.gear_sets),
                unresolved=_candidate_unresolved(candidate, detail),
            )
        )

    plan = self.plan_service.save_plan(
        name=plan_name,
        goal=goal,
        difficulty=self.difficulty_combo.currentText(),
        slots=tuple(slots),
    )
    applied_count = sum(1 for slot in slots if slot.build_name != "Composition requirement")
    self.status.success(
        f"Sent {plan.name} to Roster with {len(plan.slots)} composition chair(s); "
        f"preserved {applied_count} applied build candidate(s)."
    )
    self.rosterPlanSent.emit(plan.name)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT, _ORIGINAL_RENDER_SLOTS, _ORIGINAL_SEND_TO_ROSTER
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_RENDER_SLOTS = CompBuilderPage._render_slots
    _ORIGINAL_SEND_TO_ROSTER = CompBuilderPage._send_to_roster
    CompBuilderPage.__init__ = _comp_init_with_build_candidates
    CompBuilderPage._render_slots = _render_slots_with_candidate_refresh
    CompBuilderPage._send_to_roster = _send_to_roster_with_candidates
    _INSTALLED = True
