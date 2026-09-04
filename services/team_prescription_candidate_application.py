from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

from models.build_model import PlayerBuild

from .team_prescription import (
    PrescribedBuildChange,
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
)
from .team_prescription_candidate_ranking import PrescribedSlotCandidateRanking


def _gear_summary(build: PlayerBuild) -> str:
    names: list[str] = []

    def add(value: object) -> None:
        text = str(value or "").strip()
        if text and text not in names:
            names.append(text)

    for slot in build.Armor.values():
        add(slot.get("Set"))
        add(slot.get("Set2"))
    for slot in (
        build.FrontBarWeapon,
        build.FrontBarOffHand,
        build.BackBarWeapon,
        build.BackBarOffHand,
        build.Necklace,
        build.Ring1,
        build.Ring2,
    ):
        add(slot.Set)
        add(slot.Set2)
    return " + ".join(names)


def _metadata_list(metadata: dict[str, Any], key: str) -> tuple[str, ...]:
    value = metadata.get(key)
    if not isinstance(value, (list, tuple, set)):
        return ()
    return tuple(
        text
        for text in (str(item or "").strip() for item in value)
        if text
    )


def _change(
    roster: PrescribedRoster,
    *,
    dimension: PrescriptionDimension,
    value: str,
    reason: str,
) -> PrescribedBuildChange | None:
    normalized = str(value or "").strip()
    if not normalized or not roster.scope.allows(dimension):
        return None
    return PrescribedBuildChange(
        dimension=dimension,
        current_value=None,
        prescribed_value=normalized,
        reason=reason,
    )


def _build_snapshot_json(build: PlayerBuild) -> str:
    return json.dumps(
        build.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def apply_ranked_candidate_to_prescribed_roster(
    *,
    roster: PrescribedRoster,
    ranking: PrescribedSlotCandidateRanking,
) -> PrescribedRoster:
    """Apply one defensible slot recommendation without mutating saved builds."""

    target_index = next(
        (
            index
            for index, assignment in enumerate(roster.assignments)
            if assignment.slot_name.casefold() == ranking.slot_name.casefold()
        ),
        None,
    )
    if target_index is None:
        raise ValueError(f"prescribed roster has no slot named {ranking.slot_name!r}")

    current = roster.assignments[target_index]
    if current.player_name is not None:
        raise ValueError(
            f"cannot replace anchored saved player in prescribed slot {current.slot_name!r}"
        )

    if ranking.recommended is None:
        if not ranking.unresolved:
            return roster
        assignments = list(roster.assignments)
        assignments[target_index] = replace(
            current,
            unresolved=tuple(dict.fromkeys(current.unresolved + ranking.unresolved)),
        )
        return replace(roster, assignments=tuple(assignments))

    evidence = ranking.recommended
    comparison = evidence.comparison
    build = evidence.candidate_build
    provider_ids = evidence.provider_requirement_ids
    provider_reason = (
        " and satisfies allocated provider requirements " + ", ".join(provider_ids)
        if provider_ids
        else ""
    )
    if comparison is not None:
        objective_detail = f"modeled objective delta {comparison.delta:+.3f}"
    else:
        assert evidence.open_slot is not None
        measurement = evidence.open_slot.measurement
        objective_detail = (
            f"absolute {measurement.metric_name} {float(measurement.value):.3f}"
        )
    objective_reason = (
        f"Evidence ranked candidate {evidence.candidate_id!r} for "
        f"{current.slot_name} with {objective_detail}{provider_reason}."
    )

    open_candidate = (
        evidence.open_slot.candidate if evidence.open_slot is not None else None
    )
    saved_player_name = open_candidate.player_name if open_candidate is not None else None

    assignments = list(roster.assignments)
    new_assignment_unresolved: tuple[str, ...] = ()
    if saved_player_name:
        assignments[target_index] = PrescribedRosterAssignment(
            slot_name=current.slot_name,
            player_name=saved_player_name,
            source_build_name=build.BuildName.strip() or None,
            prescribed_role=current.prescribed_role,
            changes=(),
            unresolved=(),
            prescribed_build_json=open_candidate.candidate_build_json,
        )
        assumptions = tuple(dict.fromkeys((*roster.assumptions, objective_reason)))
    elif open_candidate is not None and not open_candidate.has_complete_build_snapshot:
        metadata = open_candidate.candidate_metadata
        observed_gear = " + ".join(_metadata_list(metadata, "observed_gear_sets"))
        observed_skills = " / ".join(_metadata_list(metadata, "observed_skills"))
        observed_mundus = str(metadata.get("observed_mundus") or build.Mundus or "").strip()
        proposed = (
            _change(
                roster,
                dimension=PrescriptionDimension.CLASS,
                value=(build.EsoClass or str(metadata.get("observed_class") or "")),
                reason=objective_reason,
            ),
            _change(
                roster,
                dimension=PrescriptionDimension.BUILD,
                value=build.BuildName,
                reason=objective_reason,
            ),
            _change(
                roster,
                dimension=PrescriptionDimension.GEAR,
                value=observed_gear,
                reason=objective_reason,
            ),
            _change(
                roster,
                dimension=PrescriptionDimension.SKILLS,
                value=observed_skills,
                reason=objective_reason,
            ),
            _change(
                roster,
                dimension=PrescriptionDimension.MUNDUS,
                value=observed_mundus,
                reason=objective_reason,
            ),
        )
        changes = tuple(change for change in proposed if change is not None)
        unknown_fields = _metadata_list(metadata, "unknown_fields")
        if unknown_fields:
            new_assignment_unresolved = (
                f"{current.slot_name}: observed template leaves unresolved: "
                + ", ".join(unknown_fields),
            )
        assignments[target_index] = PrescribedRosterAssignment(
            slot_name=current.slot_name,
            player_name=None,
            source_build_name=build.BuildName.strip() or None,
            prescribed_role=current.prescribed_role,
            changes=changes,
            unresolved=new_assignment_unresolved,
            prescribed_build_json=None,
        )
        source_note = str(metadata.get("source_url") or open_candidate.candidate_source).strip()
        assumptions = tuple(
            dict.fromkeys(
                (
                    *roster.assumptions,
                    objective_reason,
                    f"{current.slot_name}: partial template source {source_note}",
                )
            )
        )
    else:
        proposed = (
            _change(roster, dimension=PrescriptionDimension.CLASS, value=build.EsoClass, reason=objective_reason),
            _change(roster, dimension=PrescriptionDimension.RACE, value=build.Race, reason=objective_reason),
            _change(roster, dimension=PrescriptionDimension.BUILD, value=build.BuildName, reason=objective_reason),
            _change(roster, dimension=PrescriptionDimension.GEAR, value=_gear_summary(build), reason=objective_reason),
        )
        changes = tuple(change for change in proposed if change is not None)
        assignments[target_index] = PrescribedRosterAssignment(
            slot_name=current.slot_name,
            player_name=None,
            source_build_name=build.BuildName.strip() or None,
            prescribed_role=current.prescribed_role,
            changes=changes,
            unresolved=(),
            prescribed_build_json=(
                open_candidate.candidate_build_json
                if open_candidate is not None
                else _build_snapshot_json(build)
            ),
        )
        assumptions = roster.assumptions

    prefix = current.slot_name.casefold() + ":"
    remaining_unresolved = tuple(
        item for item in roster.unresolved if not str(item).casefold().startswith(prefix)
    )
    if new_assignment_unresolved:
        remaining_unresolved = tuple(
            dict.fromkeys((*remaining_unresolved, *new_assignment_unresolved))
        )
    return replace(
        roster,
        assignments=tuple(assignments),
        assumptions=assumptions,
        unresolved=remaining_unresolved,
    )
