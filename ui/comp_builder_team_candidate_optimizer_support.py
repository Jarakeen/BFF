from __future__ import annotations

from engine.config import get_data_dir
from services.comp_builder_provider_evidence import CompBuilderProviderEvidenceService
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

    provider_service = getattr(page, "_comp_provider_evidence_service", None)
    if provider_service is None:
        provider_service = CompBuilderProviderEvidenceService(get_data_dir())
        page._comp_provider_evidence_service = provider_service

    applied = getattr(page, "_comp_applied_candidates", {})
    used_saved_players = tuple(support._used_saved_players(page))
    pools: list[CompTeamCandidatePool] = []
    rows_by_slot: dict[str, int] = {}
    provider_ids_by_candidate: dict[str, tuple[str, ...]] = {}
    unresolved_reads: list[str] = []
    unresolved_provider_mappings: list[str] = []
    skipped_existing = 0

    required_team_provider_ids = tuple(
        row.capability_type
        for row in provider_service.profile.mapped_required
        if row.capability_type
    )
    already_covered_team_provider_ids: set[str] = set()
    for slot_name, candidate in applied.items():
        skipped_existing += 1
        try:
            already_covered_team_provider_ids.update(
                provider_service.provider_ids_for_candidate(candidate)
            )
        except Exception as exc:
            unresolved_reads.append(
                f"{slot_name}: provider evidence for {candidate.name} could not be resolved: {exc}"
            )

    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        if slot_name in applied:
            continue
        try:
            candidates = support._chair_candidates(page, row)
        except (OSError, ValueError) as exc:
            unresolved_reads.append(f"{slot_name}: {exc}")
            continue

        provider_labels = page._split_values(page._cell_text(row, 6))
        provider_resolution = provider_service.resolve_requirement_labels(provider_labels)
        unresolved_provider_mappings.extend(
            f"{slot_name}: {message}"
            for message in provider_resolution.unresolved
        )

        for candidate in candidates:
            if candidate.candidate_id in provider_ids_by_candidate:
                continue
            try:
                provider_ids_by_candidate[candidate.candidate_id] = (
                    provider_service.provider_ids_for_candidate(candidate)
                )
            except Exception as exc:
                # Provider evidence failures are not converted to absence. The
                # candidate remains unable to satisfy mapped hard requirements.
                provider_ids_by_candidate[candidate.candidate_id] = ()
                unresolved_reads.append(
                    f"{slot_name}: provider evidence for {candidate.name} could not be resolved: {exc}"
                )

        pools.append(
            CompTeamCandidatePool(
                slot_name=slot_name,
                candidates=tuple(candidates),
                required_provider_ids=provider_resolution.provider_ids,
            )
        )
        rows_by_slot[slot_name] = row

    result = optimize_comp_team_candidates(
        pools=tuple(pools),
        already_used_saved_players=used_saved_players,
        provider_ids_by_candidate=provider_ids_by_candidate,
        required_team_provider_ids=required_team_provider_ids,
        already_covered_team_provider_ids=tuple(sorted(already_covered_team_provider_ids)),
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
    display_name_by_provider_id = {
        row.capability_type: row.display_name
        for row in provider_service.profile.mapped_required
        if row.capability_type
    }
    uncovered_team_provider_names = tuple(
        display_name_by_provider_id.get(provider_id, provider_id)
        for provider_id in result.uncovered_team_provider_ids
    )
    unresolved = [
        *(
            f"raid-wide provider still uncovered: {name}"
            for name in uncovered_team_provider_names
        ),
        *(
            f"{slot}: no candidate proved the chair's mapped provider requirement"
            for slot in result.provider_blocked_slots
        ),
        *(
            f"{slot}: no coherent matching candidate"
            for slot in result.unresolved_slots
            if slot not in result.provider_blocked_slots
        ),
        *unresolved_provider_mappings,
        *unresolved_reads,
    ]
    if unresolved:
        page.status.warning(message + " " + " • ".join(unresolved[:5]))
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
