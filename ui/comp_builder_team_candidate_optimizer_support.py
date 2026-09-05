from __future__ import annotations

from services.comp_builder_team_candidate_optimizer import (
    CompTeamCandidatePool,
    optimize_comp_team_candidates,
)


_INSTALLED = False


def _apply_best_candidates_to_all_optimized(page, *_args) -> None:
    from ui import comp_builder_build_candidate_support as support

    if page.matrix_table.rowCount() <= 0:
        page.status.warning("There are no composition chairs to fill.")
        return

    applied = getattr(page, "_comp_applied_candidates", {})
    used_saved_players = tuple(support._used_saved_players(page))
    pools: list[CompTeamCandidatePool] = []
    rows_by_slot: dict[str, int] = {}
    unresolved_reads: list[str] = []
    skipped_existing = 0

    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        if slot_name in applied:
            skipped_existing += 1
            continue
        try:
            candidates = support._chair_candidates(page, row)
        except (OSError, ValueError) as exc:
            unresolved_reads.append(f"{slot_name}: {exc}")
            continue
        pools.append(
            CompTeamCandidatePool(
                slot_name=slot_name,
                candidates=tuple(candidates),
            )
        )
        rows_by_slot[slot_name] = row

    result = optimize_comp_team_candidates(
        pools=tuple(pools),
        already_used_saved_players=used_saved_players,
    )

    for assignment in result.assignments:
        candidate = assignment.candidate
        if candidate is None:
            continue
        row = rows_by_slot[assignment.slot_name]
        support._set_candidate_for_row(page, row, candidate)

    support._refresh_candidates(page)
    open_count = page.matrix_table.rowCount() - len(page._comp_applied_candidates)
    message = (
        f"Optimized the remaining team and applied {result.applied_count} candidate(s); "
        f"preserved {skipped_existing} existing choice(s); {open_count} chair(s) remain open."
    )
    unresolved = [
        *(f"{slot}: no coherent matching candidate" for slot in result.unresolved_slots),
        *unresolved_reads,
    ]
    if unresolved:
        page.status.warning(message + " " + " • ".join(unresolved[:4]))
    else:
        page.status.success(message)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as support

    # The existing button callback resolves this module global at click time, so
    # replacing the function keeps the established UI wiring while upgrading only
    # the bulk-selection policy from greedy chair order to whole-team optimization.
    support._apply_best_candidates_to_all = _apply_best_candidates_to_all_optimized
    _INSTALLED = True
