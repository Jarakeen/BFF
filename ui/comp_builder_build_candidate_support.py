from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QScrollArea

from engine.config import get_data_dir
from services.comp_builder_build_candidates import (
    CompBuildCandidate,
    CompBuilderBuildCandidateService,
)
from services.generated_roster_plan_service import GeneratedRosterDraftSlot
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
    if candidate.source_kind == "esologs_snapshot":
        return f"ESO Logs • {candidate.source_name}"
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


def _roster_member_for_row(page, row: int):
    if row < 0:
        return None
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    return getattr(page, "_comp_roster_member_by_slot", {}).get(slot_name)


def _row_is_recruit(page, row: int) -> bool:
    if row < 0 or page.matrix_table.columnCount() <= 11:
        return False
    value = page._cell_text(row, 11).casefold()
    return value in {"recruit", "recruitment needed"} or value.startswith("recruit ")


def _candidate_matches_roster_member(candidate: CompBuildCandidate, member, *, recruit: bool = False) -> bool:
    """Saved-build candidates must belong to the loaded player; references remain advice."""
    if recruit and candidate.source_kind == "saved_build":
        return False
    if member is None or candidate.source_kind != "saved_build":
        return True

    member_player_id = str(
        getattr(member, "CanonicalPlayerId", "") or ""
    ).strip().casefold()
    member_character_id = str(
        getattr(member, "CanonicalCharacterId", "") or ""
    ).strip().casefold()
    candidate_player_id = str(candidate.saved_player_id or "").strip().casefold()
    candidate_character_id = str(candidate.saved_character_id or "").strip().casefold()

    if member_player_id and candidate_player_id:
        return member_player_id == candidate_player_id
    if member_character_id and candidate_character_id:
        return member_character_id == candidate_character_id

    # Compatibility-only fallback for historical roster rows that predate canonical ids.
    identities = {
        " ".join(str(value or "").strip().casefold().split())
        for value in (
            getattr(member, "PlayerName", ""),
            getattr(member, "CharacterName", ""),
        )
        if str(value or "").strip()
    }
    source = " ".join(str(candidate.source_name or "").strip().casefold().split())
    return bool(source and source in identities)


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
    member = _roster_member_for_row(page, row)
    recruit = _row_is_recruit(page, row)
    member_key = (
        str(getattr(member, "Gamertag", "") or "").strip().casefold(),
        str(getattr(member, "Name", "") or "").strip().casefold(),
        str(getattr(member, "CharacterId", "") or "").strip().casefold(),
    )
    cache_key = (
        goal,
        slot_name,
        role,
        preferred_class,
        observed_gear,
        observed_skills,
        member_key,
        recruit,
    )
    cache = getattr(page, "_comp_chair_candidate_cache", None)
    if cache is None:
        cache = {}
        page._comp_chair_candidate_cache = cache
    if cache_key in cache:
        return cache[cache_key]

    candidates = page._comp_build_candidate_service.candidates_for_chair(
        goal=goal,
        slot_name=slot_name,
        role=role,
        preferred_class=preferred_class,
        observed_gear_sets=observed_gear,
        observed_skills=observed_skills,
    )
    result = tuple(
        candidate
        for candidate in candidates
        if _candidate_matches_roster_member(candidate, member, recruit=recruit)
    )
    # This cache only avoids duplicate UI repaint work. Keep it small and local.
    if len(cache) >= 64:
        cache.clear()
    cache[cache_key] = result
    return result


def _saved_player_key(candidate: CompBuildCandidate) -> str:
    if candidate.source_kind != "saved_build":
        return ""
    for value in (
        candidate.saved_player_id,
        candidate.saved_character_id,
        candidate.saved_build_id,
        candidate.candidate_id,
    ):
        key = str(value or "").strip().casefold()
        if key:
            return key
    return ""


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
    state = getattr(page, "_comp_plan_state", None)
    canonical = {
        key
        for chair in tuple(getattr(state, "chairs", ()) or ())
        if str(chair.build_source_kind or "").strip().casefold() == "saved_build"
        if (
            key := str(
                chair.player_id
                or chair.character_id
                or chair.selected_build_id
                or chair.candidate_id
                or ""
            ).strip().casefold()
        )
    }
    mirror = {
        key
        for candidate in getattr(page, "_comp_applied_candidates", {}).values()
        if (key := _saved_player_key(candidate))
    }
    return canonical | mirror


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
    chair = _state_chair_for_row(page, row)
    if applied is None and chair is not None and chair.candidate_id:
        applied = next(
            (
                candidate
                for candidate in candidates
                if candidate.candidate_id == chair.candidate_id
            ),
            None,
        )
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


def _state_chair_for_row(page, row: int):
    state = getattr(page, "_comp_plan_state", None)
    if state is None or row < 0:
        return None
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    wanted = "-".join(
        str(slot_name or "")
        .strip()
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )
    return next(
        (
            chair
            for chair in tuple(getattr(state, "chairs", ()) or ())
            if "-".join(
                str(getattr(chair, "seat_id", "") or "")
                .strip()
                .casefold()
                .replace("_", " ")
                .replace("-", " ")
                .split()
            )
            == wanted
        ),
        None,
    )


def _replace_state_chair(page, chair) -> None:
    state = getattr(page, "_comp_plan_state", None)
    if state is not None and chair is not None:
        page._comp_plan_state = state.with_chair(chair)


def _candidate_state_changes(chair, candidate: CompBuildCandidate) -> dict:
    changes: dict[str, object] = {}
    if not chair.is_locked("class") and candidate.eso_class:
        changes["eso_class"] = candidate.eso_class
    if not chair.is_locked("build"):
        if candidate.source_kind == "saved_build":
            changes["selected_build_id"] = candidate.saved_build_id or None
            changes["selected_build_name"] = candidate.name
        changes.update(
            build_source_kind=candidate.source_kind,
            build_source_name=candidate.source_name,
            build_source_url=candidate.source_url,
            candidate_id=candidate.candidate_id,
        )
    if not chair.is_locked("gear"):
        changes["planned_gear_sets"] = tuple(candidate.gear_sets)
    # Skill-package adoption is intentionally deferred to the later Comp skill-evidence
    # pass. Existing planned skills survive state round-trips but candidate application
    # does not overwrite or populate them yet.
    if not chair.is_locked("mundus"):
        changes["planned_mundus"] = candidate.mundus or None
    return changes


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
    selected = page._selected_class(row)
    chair = _state_chair_for_row(page, row)
    if chair is not None and chair.is_locked("class"):
        current = str(chair.eso_class or "Any class")
        if selected.casefold() != current.casefold():
            selector = page.matrix_table.cellWidget(row, 2)
            if isinstance(selector, QComboBox):
                selector.blockSignals(True)
                try:
                    index = selector.findText(current)
                    if index >= 0:
                        selector.setCurrentIndex(index)
                finally:
                    selector.blockSignals(False)
            page.status.warning(f"{slot_name} class is locked in this Raid Plan.")
            return
    elif chair is not None:
        _replace_state_chair(
            page,
            chair.with_changes(
                eso_class=None if selected.casefold() == "any class" else selected
            ),
        )

    applied = getattr(page, "_comp_applied_candidates", {}).get(slot_name)
    if applied is not None:
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
    chair = _state_chair_for_row(page, row)
    changes: dict[str, object] = {}
    blocked_fields: tuple[str, ...] = ()

    if chair is None:
        page.status.error(
            f"{slot_name}: candidate application requires canonical Comp planning state."
        )
    else:
        changes = _candidate_state_changes(chair, candidate)
        blocked_fields = tuple(
            field
            for field in ("class", "build", "gear", "mundus")
            if chair.is_locked(field)
        )
        if changes:
            _replace_state_chair(page, chair.with_changes(**changes))
            # Compatibility cache for older presentation helpers only.
            page._comp_applied_candidates[slot_name] = candidate

    page._comp_last_candidate_apply_changed = bool(changes)
    page._comp_last_candidate_apply_blocked_fields = blocked_fields

    if candidate.eso_class and not (chair is not None and chair.is_locked("class")):
        selector = page.matrix_table.cellWidget(row, 2)
        if isinstance(selector, QComboBox):
            index = selector.findText(candidate.eso_class)
            if index >= 0:
                selector.blockSignals(True)
                try:
                    selector.setCurrentIndex(index)
                finally:
                    selector.blockSignals(False)
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
    changed = bool(getattr(page, "_comp_last_candidate_apply_changed", False))
    blocked = tuple(
        getattr(page, "_comp_last_candidate_apply_blocked_fields", ()) or ()
    )
    if not changed:
        detail = (
            " Locked fields: " + ", ".join(blocked) + "."
            if blocked
            else ""
        )
        page.status.warning(
            f"{slot_name}: this recommendation did not change any unlocked field.{detail}"
        )
        _refresh_candidates(page)
        return

    status = "complete build" if candidate.complete_build else "partial build evidence"
    preserved = (
        " Preserved locked " + ", ".join(blocked) + "."
        if blocked
        else ""
    )
    page.status.success(
        f"Applied unlocked parts of {candidate.name} to {slot_name} as {status}."
        + preserved
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
        chair = _state_chair_for_row(page, row)
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
        if not bool(getattr(page, "_comp_last_candidate_apply_changed", False)):
            skipped_existing += 1
            continue
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
    prior_applied = dict(getattr(self, "_comp_applied_candidates", {}) or {})
    _ORIGINAL_RENDER_SLOTS(self, slots)
    if hasattr(self, "_comp_applied_candidates"):
        current_slots = {
            self._cell_text(row, 0) or f"Slot {row + 1}"
            for row in range(self.matrix_table.rowCount())
        }
        self._comp_applied_candidates = {
            slot_name: candidate
            for slot_name, candidate in prior_applied.items()
            if slot_name in current_slots
        }
        _wire_class_selectors(self)
        _refresh_candidates(self)


def _effective_candidate_gear_sets(
    candidate: CompBuildCandidate,
    manual_five_piece_sets: tuple[str, ...],
) -> tuple[str, ...]:
    """Apply manual five-piece overrides without erasing monster/mythic/arena evidence."""
    if not manual_five_piece_sets:
        return tuple(candidate.gear_sets)

    candidate_five = {
        str(value or "").strip().casefold()
        for value in tuple(candidate.five_piece_sets or ())
        if str(value or "").strip()
    }
    preserved_non_five = tuple(
        str(value).strip()
        for value in tuple(candidate.gear_sets or ())
        if str(value).strip()
        and str(value).strip().casefold() not in candidate_five
    )
    merged: list[str] = []
    seen: set[str] = set()
    for value in (*preserved_non_five, *manual_five_piece_sets):
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(value)
    return tuple(merged)


def _candidate_unresolved(candidate: CompBuildCandidate, base_detail: str) -> str:
    details = [base_detail, f"Candidate source: {_source_label(candidate)}."]
    if not candidate.complete_build:
        details.append("Candidate is partial evidence, not a complete prescribed build.")
    if candidate.unresolved:
        details.append("Unresolved: " + "; ".join(candidate.unresolved) + ".")
    return " ".join(details)


def save_generated_plan(page):
    """Persist the exact visible Comp Builder state as one generated team draft."""
    applied = getattr(page, "_comp_applied_candidates", {})
    roster_members = getattr(page, "_comp_roster_member_by_slot", {})

    goal = page.goal_combo.currentText().strip() or "Custom Goal"
    plan_name = page.plan_name_input.text().strip() or f"{goal} Composition"
    slots: list[GeneratedRosterDraftSlot] = []

    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0)
        role = page._cell_text(row, 1)
        selected_class = page._selected_class(row)
        alternatives = page._cell_text(row, 3) or "Flexible"
        required = page._cell_text(row, 4) or "Open responsibility"
        optional = page._cell_text(row, 5) or "None declared"
        providers = page._cell_text(row, 6) or "None declared"
        mechanic_jobs = page._cell_text(row, 7) or "None declared"
        detail = (
            f"Composition requirement. Alternatives: {alternatives}. "
            f"Required: {required}. Optional/flex: {optional}. "
            f"Providers: {providers}. Mechanic jobs: {mechanic_jobs}."
        )

        candidate = applied.get(slot_name)
        manual_gear_sets = tuple(
            str(value).strip()
            for value in getattr(page, "_comp_manual_gear_sets_by_slot", {}).get(slot_name, ())
            if str(value).strip()
        )
        roster_context_active = slot_name in roster_members
        roster_member = roster_members.get(slot_name)
        roster_player = (
            str(getattr(roster_member, "PlayerName", "") or "").strip()
            if roster_member is not None
            else ""
        )
        roster_character = (
            str(getattr(roster_member, "CharacterName", "") or "").strip()
            if roster_member is not None
            else ""
        )

        if candidate is None:
            concrete = selected_class != "Any class"
            known_player = bool(roster_context_active and roster_member is not None)
            slots.append(
                GeneratedRosterDraftSlot(
                    slot_name=slot_name,
                    kind="saved" if known_player else (
                        "prescribed_recruit" if concrete else "open_recruit"
                    ),
                    player_name=roster_player if known_player else "Recruitment Needed",
                    character_name=roster_character if known_player else "",
                    eso_class=selected_class,
                    build_name=(
                        "Manual gear package"
                        if manual_gear_sets
                        else "Composition requirement"
                    ),
                    gear_summary=" + ".join(manual_gear_sets),
                    unresolved=detail,
                    role=role,
                    gear_sets=manual_gear_sets,
                )
            )
            continue

        is_saved = candidate.source_kind == "saved_build"
        known_player = bool(roster_context_active and roster_member is not None)
        effective_gear_sets = _effective_candidate_gear_sets(
            candidate,
            manual_gear_sets,
        )
        slots.append(
            GeneratedRosterDraftSlot(
                slot_name=slot_name,
                kind="saved" if is_saved or known_player else "prescribed_recruit",
                player_name=roster_player if known_player else (
                    candidate.source_name if is_saved else "Recruitment Needed"
                ),
                character_name=roster_character if known_player else (
                    candidate.source_name if is_saved else ""
                ),
                eso_class=candidate.eso_class or selected_class,
                build_name=(
                    "Manual gear package"
                    if manual_gear_sets
                    else candidate.name
                ),
                gear_summary=" + ".join(effective_gear_sets),
                unresolved=_candidate_unresolved(candidate, detail),
                role=candidate.role or role,
                source_kind=candidate.source_kind,
                source_name=candidate.source_name,
                source_url=candidate.source_url,
                candidate_id=candidate.candidate_id,
                gear_sets=effective_gear_sets,
                skills=tuple(candidate.skills),
                mundus=candidate.mundus,
            )
        )

    return page.plan_service.save_plan(
        name=plan_name,
        goal=goal,
        difficulty=page.difficulty_combo.currentText(),
        slots=tuple(slots),
    )


def _send_to_roster_with_candidates(self, *_args) -> None:
    plan = save_generated_plan(self)
    applied_count = sum(
        1
        for slot in plan.slots
        if slot.build_name != "Composition requirement"
    )
    self.status.success(
        f"Prepared {plan.name} for Raid Plan with {len(plan.slots)} composition chair(s); "
        f"preserved {applied_count} applied build candidate(s)."
    )
    self.rosterPlanSent.emit(plan.name)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT, _ORIGINAL_RENDER_SLOTS
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_RENDER_SLOTS = CompBuilderPage._render_slots
    CompBuilderPage.__init__ = _comp_init_with_build_candidates
    CompBuilderPage._render_slots = _render_slots_with_candidate_refresh
    # Legacy generated-roster send remains available as compatibility code only.
    # Phase 14 owns the runtime send/save path directly to Raid Plan.
    _INSTALLED = True
