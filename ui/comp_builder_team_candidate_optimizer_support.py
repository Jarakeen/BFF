from __future__ import annotations

from engine.config import get_data_dir
from services.comp_builder_composition_style import CompCompositionStyle
from services.comp_builder_novelty_evidence import CompBuilderNoveltyEvidenceService
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
    """Fill open roster/build decisions without performing buff/debuff optimization."""
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

    # Comp Maker owns roster/build fit. Raid-wide buff/debuff optimization belongs
    # to Optimizer; Team Health remains read-only feedback about the current roster.
    used_saved_players = tuple(sorted(support._used_saved_players(page)))
    novelty_service = CompBuilderNoveltyEvidenceService(get_data_dir())
    pools: list[CompTeamCandidatePool] = []
    rows_by_slot: dict[str, int] = {}
    visible_slot_by_seat: dict[str, str] = {}
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

        pools.append(
            CompTeamCandidatePool(
                slot_name=slot_name,
                candidates=candidates,
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
    message = (
        f"Filled {result.applied_count} open roster/build decision(s) in "
        f"{style.value.replace('_', ' ')} mode; preserved "
        f"{len(result.skipped_existing)} existing/locked chair(s)."
    )
    if unresolved_reads:
        page.status.warning(message + " " + " • ".join(unresolved_reads[:5]))
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
