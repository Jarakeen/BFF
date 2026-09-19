from __future__ import annotations

from engine.config import get_data_dir
from services.comp_builder_composition_style import CompCompositionStyle
from services.comp_builder_novelty_evidence import CompBuilderNoveltyEvidenceService
from services.comp_builder_provider_evidence import CompBuilderProviderEvidenceService
from services.comp_builder_team_candidate_optimizer import (
    CompTeamCandidatePool,
    optimize_comp_team_candidates,
)


_INSTALLED = False


def _selected_style(page) -> CompCompositionStyle:
    value = getattr(page, "_comp_composition_style", CompCompositionStyle.PROVEN)
    try:
        return value if isinstance(value, CompCompositionStyle) else CompCompositionStyle(str(value))
    except ValueError:
        return CompCompositionStyle.PROVEN


def _apply_best_candidates_to_all_optimized(page, *_args) -> None:
    """Fill open roster/build decisions while satisfying assigned provider jobs."""
    from ui import comp_builder_build_candidate_support as support
    from ui.comp_builder_page import GOAL_TRIALS
    from services.comp_plan_autofill_service import CompPlanAutoFillService

    if page.matrix_table.rowCount() <= 0:
        page.status.warning("There are no composition chairs to fill.")
        return

    state = getattr(page, "_comp_plan_state", None)
    if state is None:
        page.status.error(
            "Auto-Fill requires canonical Comp planning state; state-less legacy mode "
            "is no longer supported in Phase 14."
        )
        return

    provider_service = getattr(page, "_comp_provider_evidence_service", None)
    if provider_service is None:
        provider_service = CompBuilderProviderEvidenceService(get_data_dir())
        page._comp_provider_evidence_service = provider_service

    # Assignments owns WHO. Comp Maker owns HOW. Therefore only explicit
    # primary/backup responsibilities become provider constraints here.
    required_by_seat: dict[str, tuple[str, ...]] = {}
    unresolved_provider_mappings: list[str] = []
    for chair in state.chairs:
        labels = tuple(
            label
            for label in (
                str(chair.primary_assignment or "").strip(),
                str(chair.secondary_assignment or "").strip(),
            )
            if label
        )
        if not labels:
            continue
        resolution = provider_service.resolve_requirement_labels(labels)
        required_by_seat[chair.seat_id] = resolution.provider_ids
        unresolved_provider_mappings.extend(
            f"{chair.seat_id}: {message}"
            for message in resolution.unresolved
        )

    used_saved_players = tuple(sorted(support._used_saved_players(page)))
    novelty_service = CompBuilderNoveltyEvidenceService(get_data_dir())
    pools: list[CompTeamCandidatePool] = []
    rows_by_slot: dict[str, int] = {}
    visible_slot_by_seat: dict[str, str] = {}
    provider_ids_by_candidate: dict[str, tuple[str, ...]] = {}
    novelty_by_candidate: dict[str, float] = {}
    novelty_evidence_by_candidate: dict[str, object] = {}
    unresolved_reads: list[str] = []

    goal = page.goal_combo.currentText().strip()
    trial_name = GOAL_TRIALS.get(goal, "")

    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        chair_state = support._state_chair_for_row(page, row)

        try:
            candidates = tuple(
                candidate
                for candidate in support._chair_candidates(page, row)
                if candidate.source_kind in {"saved_build", "reference_template"}
            )
        except (OSError, ValueError) as exc:
            unresolved_reads.append(f"{slot_name}: {exc}")
            continue

        if (
            chair_state is not None
            and not CompPlanAutoFillService.chair_is_open_for_build_autofill(chair_state)
        ):
            candidates = ()

        for candidate in candidates:
            if candidate.candidate_id in provider_ids_by_candidate:
                continue
            try:
                provider_ids_by_candidate[candidate.candidate_id] = (
                    provider_service.provider_ids_for_candidate(candidate)
                )
            except (OSError, TypeError, ValueError) as exc:
                provider_ids_by_candidate[candidate.candidate_id] = ()
                unresolved_reads.append(
                    f"{slot_name}: provider evidence for {candidate.name} could not be resolved: {exc}"
                )

        try:
            novelty_result = novelty_service.evaluate_candidates(
                candidates,
                role=page._cell_text(row, 1),
                trial_name=trial_name,
            )
            novelty_by_candidate.update(novelty_result.novelty_by_candidate)
            novelty_evidence_by_candidate.update(
                {item.candidate_id: item for item in novelty_result.evidence}
            )
        except (OSError, ValueError) as exc:
            unresolved_reads.append(
                f"{slot_name}: roster/build evidence could not be resolved: {exc}"
            )

        local_required = (
            required_by_seat.get(chair_state.seat_id, ())
            if chair_state is not None
            else ()
        )
        pools.append(
            CompTeamCandidatePool(
                slot_name=slot_name,
                candidates=candidates,
                required_provider_ids=tuple(local_required),
            )
        )
        rows_by_slot[slot_name] = row
        if chair_state is not None:
            visible_slot_by_seat[str(chair_state.seat_id)] = slot_name

    page._comp_novelty_by_candidate = dict(novelty_by_candidate)
    page._comp_novelty_evidence_by_candidate = dict(novelty_evidence_by_candidate)
    style = _selected_style(page)

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=tuple(pools),
        already_used_saved_players=used_saved_players,
        provider_ids_by_candidate=provider_ids_by_candidate,
        composition_style=style,
        novelty_by_candidate=novelty_by_candidate,
    )
    page._comp_plan_state = result.state

    candidate_by_id = {
        candidate.candidate_id: candidate
        for pool in pools
        for candidate in pool.candidates
    }
    for change in result.changes:
        candidate = candidate_by_id.get(change.candidate_id)
        visible_slot = visible_slot_by_seat.get(change.seat_id, change.seat_id)
        row = rows_by_slot.get(visible_slot)
        if candidate is not None and row is not None:
            # Compatibility mirror only. Canonical CompPlanState already owns the
            # applied decision and Save never reads this mirror.
            page._comp_applied_candidates[visible_slot] = candidate

    support._refresh_candidates(page)
    blocked = tuple(result.optimization.provider_blocked_slots)
    message = (
        f"Filled {result.applied_count} open roster/build decision(s) in "
        f"{style.value.replace('_', ' ')} mode; preserved "
        f"{len(result.skipped_existing)} existing/locked chair(s)."
    )
    warnings = [
        *(
            f"{slot}: no candidate currently proves the assigned provider job"
            for slot in blocked
        ),
        *unresolved_provider_mappings,
        *unresolved_reads,
    ]
    if warnings:
        page.status.warning(message + " " + " • ".join(warnings[:5]))
    else:
        page.status.success(message)
    return


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as support

    support._apply_best_candidates_to_all = _apply_best_candidates_to_all_optimized
    _INSTALLED = True
