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

    state = getattr(page, "_comp_plan_state", None)
    applied = getattr(page, "_comp_applied_candidates", {})
    used_saved_players = tuple(support._used_saved_players(page))
    pools: list[CompTeamCandidatePool] = []
    rows_by_slot: dict[str, int] = {}
    visible_slot_by_seat: dict[str, str] = {}
    provider_ids_by_candidate: dict[str, tuple[str, ...]] = {}
    novelty_by_candidate: dict[str, float] = {}
    novelty_evidence_by_candidate: dict[str, object] = {}
    unresolved_reads: list[str] = []
    unresolved_provider_mappings: list[str] = []

    required_team_provider_ids: list[str] = []
    provider_resolution_by_slot: dict[str, object] = {}

    # Canonical Raid Plan-bound sessions derive provider needs from CompPlanState Team
    # Health plus explicit chair assignments. Legacy/unbound sessions retain the old
    # template-row provider requirements until that compatibility path is retired.
    if state is not None:
        from engine.config import DEFAULT_DATABASE
        from services.comp_plan_health_service import CompPlanHealthService

        health = CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)
        labels = list(health.missing_required)
        labels.extend(
            review.effect_name
            for review in health.assignment_reviews
            if review.state == "assigned_unproven"
        )
        resolution = provider_service.resolve_requirement_labels(
            tuple(dict.fromkeys(labels))
        )
        required_team_provider_ids.extend(resolution.provider_ids)
        unresolved_provider_mappings.extend(resolution.unresolved)
    else:
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
    if state is not None:
        from engine.config import DEFAULT_DATABASE
        from services.comp_plan_health_service import CompPlanHealthService

        health = CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)
        covered_labels = tuple(
            dict.fromkeys(
                (*health.covered_required, *health.conditional_required)
            )
        )
        covered_resolution = provider_service.resolve_requirement_labels(covered_labels)
        already_covered_team_provider_ids.update(covered_resolution.provider_ids)
        unresolved_provider_mappings.extend(covered_resolution.unresolved)
    else:
        for slot_name, candidate in applied.items():
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
        chair_state = (
            support._state_chair_for_row(page, row)
            if state is not None
            else None
        )

        if state is None and slot_name in applied:
            continue

        try:
            candidates = tuple(
                candidate
                for candidate in support._chair_candidates(page, row)
                if candidate.source_kind in {"saved_build", "reference_template"}
            )
        except (OSError, ValueError) as exc:
            unresolved_reads.append(f"{slot_name}: {exc}")
            continue

        if state is not None and chair_state is not None:
            from services.comp_plan_autofill_service import CompPlanAutoFillService

            if not CompPlanAutoFillService.chair_is_open_for_build_autofill(chair_state):
                candidates = ()

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

        local_required = ()
        if state is None:
            provider_resolution = provider_resolution_by_slot[slot_name]
            local_required = provider_resolution.provider_ids

        pools.append(
            CompTeamCandidatePool(
                slot_name=slot_name,
                candidates=candidates,
                required_provider_ids=local_required,
            )
        )
        rows_by_slot[slot_name] = row
        if chair_state is not None:
            visible_slot_by_seat[str(chair_state.seat_id)] = slot_name

    page._comp_novelty_by_candidate = dict(novelty_by_candidate)
    page._comp_novelty_evidence_by_candidate = dict(novelty_evidence_by_candidate)
    style = _selected_style(page)

    if state is not None:
        from services.comp_plan_autofill_service import CompPlanAutoFillService

        result = CompPlanAutoFillService().apply(
            state=state,
            pools=tuple(pools),
            already_used_saved_players=used_saved_players,
            provider_ids_by_candidate=provider_ids_by_candidate,
            required_team_provider_ids=tuple(required_team_provider_ids),
            already_covered_team_provider_ids=tuple(
                sorted(already_covered_team_provider_ids)
            ),
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
            f"Auto-filled {result.applied_count} open build decision(s) in "
            f"{style.value.replace('_', ' ')} mode; preserved "
            f"{len(result.skipped_existing)} existing/locked chair(s)."
        )
        unresolved = [
            *(
                f"raid-wide provider still uncovered: {provider_id}"
                for provider_id in result.optimization.uncovered_team_provider_ids
            ),
            *unresolved_provider_mappings,
            *unresolved_reads,
        ]
        if unresolved:
            page.status.warning(message + " " + " • ".join(unresolved[:5]))
        else:
            page.status.success(message)
        return

    # Legacy/ad-hoc path remains temporarily unchanged in ownership.
    result = optimize_comp_team_candidates(
        pools=tuple(pools),
        already_used_saved_players=used_saved_players,
        provider_ids_by_candidate=provider_ids_by_candidate,
        required_team_provider_ids=tuple(required_team_provider_ids),
        already_covered_team_provider_ids=tuple(
            sorted(already_covered_team_provider_ids)
        ),
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
        f"Filled {result.applied_count} open chair(s) from saved/reference candidates in "
        f"{style.value.replace('_', ' ')} mode; {open_count} chair(s) remain open."
    )
    unresolved = [
        *(f"raid-wide provider still uncovered: {provider_id}" for provider_id in result.uncovered_team_provider_ids),
        *(
            f"{slot}: no candidate proved the chair's mapped provider requirement"
            for slot in result.provider_blocked_slots
        ),
        *(
            f"{slot}: no matching candidate"
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
