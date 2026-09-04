from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.team_prescription import PrescribedRoster
from services.team_prescription_observed_templates import (
    ObservedTeamTemplateStore,
    ObservedTemplateObjectiveEvaluator,
    observed_template_candidates,
)
from services.team_prescription_pipeline import (
    run_automatic_team_prescription_candidate_pipeline,
)
from services.team_prescription_slot_constraints import PrescribedSlotBuildConstraint
from services.team_prescription_template_catalog import (
    TemplateCatalogObjectiveEvaluator,
    TeamPrescriptionTemplateCatalog,
    catalog_candidates,
)


@dataclass(frozen=True)
class TeamTemplateSourcePassResult:
    final_roster: PrescribedRoster
    published_template_count: int
    observed_template_count: int
    applied_count: int
    unresolved: tuple[str, ...] = ()


def apply_team_template_sources(
    *,
    roster: PrescribedRoster,
    goal: str,
    data_dir: str | Path,
    build_constraints_by_slot: dict[str, PrescribedSlotBuildConstraint] | None = None,
) -> TeamTemplateSourcePassResult:
    """Fill open chairs from local versioned template evidence.

    Published/curated templates have first priority. Their explicit ``complete_build``
    declaration determines whether the result is a saveable full snapshot or a partial
    recommendation. Once either form is selected for a chair, the lower-priority
    user-curated observed-performance source does not overwrite it. Observed ESO Logs
    templates therefore fill only chairs that remain genuinely open.
    """

    root = Path(data_dir)
    current = roster
    unresolved: list[str] = []
    applied_count = 0

    published = TeamPrescriptionTemplateCatalog(
        root / "team_prescription_templates.json"
    ).load()
    if published.templates:
        result = run_automatic_team_prescription_candidate_pipeline(
            roster=current,
            candidates=catalog_candidates(published),
            evaluate_objective=TemplateCatalogObjectiveEvaluator(
                published,
                goal=goal,
            ),
            build_constraints_by_slot=build_constraints_by_slot,
        )
        current = result.final_roster
        applied_count += result.optimization.applied_count
        unresolved.extend(result.unresolved)

    observed = ObservedTeamTemplateStore(
        root / "team_prescription_observed_templates.json"
    ).load()
    if observed.templates:
        result = run_automatic_team_prescription_candidate_pipeline(
            roster=current,
            candidates=observed_template_candidates(observed),
            evaluate_objective=ObservedTemplateObjectiveEvaluator(observed),
            build_constraints_by_slot=build_constraints_by_slot,
        )
        current = result.final_roster
        applied_count += result.optimization.applied_count
        unresolved.extend(result.unresolved)

    # A first source may report an open slot that a later source successfully fills.
    # Only surface source-level unresolved messages whose slot is genuinely open in
    # the final roster. Global/non-slot messages remain visible.
    open_slot_prefixes = {
        assignment.slot_name.casefold() + ":"
        for assignment in current.assignments
        if assignment.is_open_for_candidate
    }
    filtered: list[str] = []
    for message in unresolved:
        text = str(message or "").strip()
        if not text:
            continue
        lowered = text.casefold()
        prefix = next(
            (prefix for prefix in open_slot_prefixes if lowered.startswith(prefix)),
            None,
        )
        if prefix is not None or not any(
            lowered.startswith(assignment.slot_name.casefold() + ":")
            for assignment in current.assignments
        ):
            filtered.append(text)

    return TeamTemplateSourcePassResult(
        final_roster=current,
        published_template_count=len(published.templates),
        observed_template_count=len(observed.templates),
        applied_count=applied_count,
        unresolved=tuple(dict.fromkeys(filtered)),
    )
