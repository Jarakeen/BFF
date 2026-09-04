from __future__ import annotations

from .team_prescription import PrescribedRoster, PrescriptionDimension


def _change_value(assignment, dimension: PrescriptionDimension) -> str | None:
    change = assignment.change_for(dimension)
    if change is None:
        return None
    value = str(change.prescribed_value or "").strip()
    return value or None


def format_prescribed_roster_preview(roster: PrescribedRoster) -> tuple[str, ...]:
    """Return stable human-readable lines for a non-destructive roster prescription.

    The formatter distinguishes saved anchors, complete build snapshots, partial
    evidence-backed templates, and unresolved open slots without inventing player
    identities or gameplay evidence.
    """

    lines: list[str] = [roster.name]
    for assignment in roster.assignments:
        if assignment.player_name:
            source = assignment.source_build_name or "Current Build"
            lines.append(f"{assignment.slot_name}: {assignment.player_name} — {source}")
            continue

        prescribed_class = _change_value(assignment, PrescriptionDimension.CLASS)
        prescribed_build = _change_value(assignment, PrescriptionDimension.BUILD)
        prescribed_gear = _change_value(assignment, PrescriptionDimension.GEAR)
        prescribed_race = _change_value(assignment, PrescriptionDimension.RACE)
        prescribed_skills = _change_value(assignment, PrescriptionDimension.SKILLS)
        prescribed_mundus = _change_value(assignment, PrescriptionDimension.MUNDUS)
        prescribed_food = _change_value(assignment, PrescriptionDimension.FOOD)
        prescribed_potion = _change_value(assignment, PrescriptionDimension.POTION)

        if any(
            (
                prescribed_class,
                prescribed_build,
                prescribed_gear,
                prescribed_race,
                prescribed_skills,
                prescribed_mundus,
                prescribed_food,
                prescribed_potion,
            )
        ):
            summary = [assignment.prescribed_role]
            if prescribed_class:
                summary.append(prescribed_class)
            if prescribed_race:
                summary.append(prescribed_race)
            if prescribed_build:
                summary.append(prescribed_build)
            lines.append(f"{assignment.slot_name}: PRESCRIBED — " + " | ".join(summary))
            if prescribed_gear:
                lines.append(f"  Gear: {prescribed_gear}")
            if prescribed_skills:
                lines.append(f"  Skills observed: {prescribed_skills}")
            if prescribed_mundus:
                lines.append(f"  Mundus: {prescribed_mundus}")
            if prescribed_food:
                lines.append(f"  Food: {prescribed_food}")
            if prescribed_potion:
                lines.append(f"  Potion: {prescribed_potion}")
            for unresolved in assignment.unresolved:
                lines.append(f"  Unresolved: {unresolved}")
            continue

        lines.append(
            f"{assignment.slot_name}: TO PRESCRIBE ({assignment.prescribed_role})"
        )
        for unresolved in assignment.unresolved:
            lines.append(f"  Unresolved: {unresolved}")

    lines.append("")
    lines.append(
        f"{len(roster.unresolved)} unresolved roster requirement(s) remain."
    )
    return tuple(lines)
