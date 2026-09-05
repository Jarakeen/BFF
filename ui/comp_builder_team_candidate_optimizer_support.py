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
    from ui import comp_builder_build_candidate_support as support
    from ui.comp_builder_page import GOAL_TRIALS

    if page.matrix_table.rowCount() <= 0:
        page.status.warning("There are no composition chairs to fill.")
        return

    provider_service = getattr(page, "_comp_provider_evidence_service", None)
    if provider_service is None:
        provider_service = CompBuilderProviderEvidenceService(get_data_dir())
        page._comp_provider_evidence_service = provider_service
    novelty_service = CompBuilderNoveltyEvidenceService(get_data_dir())

    applied = getattr(page, "_comp_applied_candidates", {})
    used_saved_players = tuple(support._used_saved_players(page))
    pools: list[CompTeamCandidatePool] = []
    rows_by_slot: dict[str, int] = {}
    provider_ids_by_candidate: dict[str, tuple[str, ...]] = {}
    novelty_by_candidate: dict[str, float] = {}
    novelty_evidence_by_candidate: dict[str, object] = {}
    unresolved_reads: list[str] = []
    unresolved_provider_mappings: list[str] = []
    skipped_existing = 0

    required_team_provider_ids: list[str] = []
    provider_resolution_by_slot: dict[str, object] = {}
    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        provider_labels = page._split_values(page._cell_text(row, 6))
        provider_resolution = provider_service.resolve_requirement_labels(provider_labels)
        provider_resolution_by_slot[slot_name] = provider_resolution
        required_team_provider_ids.extend(provider_resolution.provider_ids)
        unresolved_provider_mappings.extend(
            f"{slot_name}: {message}"
            for message in provider_resolution.unresolved
        )
    required_team_provider_ids = list(dict.fromkeys(required_team_provider_ids))

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

    goal = page.goal_combo.currentText().strip()
    trial_name = GOAL_TRIALS.get(goal, "")

    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        if slot_name in applied:
            continue
        try:
            # This action is explicitly Fill from Roster. Reference templates remain
            # visible in the manual build picker, but they cannot masquerade as saved
            # players during automatic roster fill.
            candidates = tuple(
                candidate
                for candidate in support._chair_candidates(page, row)
                if candidate.source_kind == "saved_build"
            )
        except (OSError, ValueError) as exc:
            unresolved_reads.append(f"{slot_name}: {exc}")
            continue

        provider_resolution = provider_resolution_by_slot[slot_name]

        for candidate in candidates:
            if candidate.candidate_id in provider_ids_by_candidate:
                continue
            try:
                provider_ids_by_candidate[candidate.candidate_id] = (
                    provider_service.provider_ids_for_candidate(candidate)
                )
            except Exception as exc:
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
                f"{slot_name}: novelty evidence could not be resolved: {exc}"
            )

        pools.append(
            CompTeamCandidatePool(
                slot_name=slot_name,
                candidates=candidates,
                required_provider_ids=provider_resolution.provider_ids,
            )
        )
        rows_by_slot[slot_name] = row

    page._comp_novelty_by_candidate = dict(novelty_by_candidate)
    page._comp_novelty_evidence_by_candidate = dict(novelty_evidence_by_candidate)
    style = _selected_style(page)
    result = optimize_comp_team_candidates(
        pools=tuple(pools),
        already_used_saved_players=used_saved_players,
        provider_ids_by_candidate=provider_ids_by_candidate,
        required_team_provider_ids=tuple(required_team_provider_ids),
        already_covered_team_provider_ids=tuple(sorted(already_covered_team_provider_ids)),
        composition_style=style,
        novelty_by_candidate=novelty_by_candidate,
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
        f"Filled {result.applied_count} open chair(s) from saved roster builds in "
        f"{style.value.replace('_', ' ')} mode; preserved {skipped_existing} existing choice(s); "
        f"{open_count} chair(s) remain open."
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
            f"{slot}: no roster build proved the chair's mapped provider requirement"
            for slot in result.provider_blocked_slots
        ),
        *(
            f"{slot}: no matching saved roster build"
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

    support._apply_best_candidates_to_all = _apply_best_candidates_to_all_optimized
    _INSTALLED = True
