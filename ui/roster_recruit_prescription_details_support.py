from __future__ import annotations


_INSTALLED = False


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _format_prescription_evidence(value: dict[str, object]) -> str:
    lines = ["", "ORIGINAL RECRUIT PRESCRIPTION"]
    eso_class = _clean(value.get("eso_class"))
    role = _clean(value.get("role"))
    build_name = _clean(value.get("build_name"))
    source_name = _clean(value.get("source_name"))
    source_kind = _clean(value.get("source_kind"))
    candidate_id = _clean(value.get("candidate_id"))
    mundus = _clean(value.get("mundus"))
    unresolved = _clean(value.get("unresolved"))

    if eso_class:
        lines.append(f"Class: {eso_class}")
    if role:
        lines.append(f"Role: {role}")
    if build_name:
        lines.append(f"Build evidence: {build_name}")
    if source_name or source_kind:
        lines.append(f"Source: {source_name or source_kind.replace('_', ' ').title()}")
    if candidate_id:
        lines.append(f"Candidate: {candidate_id}")

    gear = tuple(_clean(item) for item in (value.get("gear_sets") or ()) if _clean(item))
    if gear:
        lines.extend(("", "PRESCRIBED / OBSERVED GEAR SETS"))
        lines.extend(f"• {item}" for item in gear)

    skills = tuple(_clean(item) for item in (value.get("skills") or ()) if _clean(item))
    if skills:
        lines.extend(("", "PRESCRIBED / OBSERVED ABILITIES"))
        lines.extend(f"• {item}" for item in skills)

    if mundus:
        lines.extend(("", "PRESCRIBED MUNDUS", mundus))
    if unresolved:
        lines.extend(("", "PRESCRIPTION UNRESOLVED", unresolved))

    lines.extend(
        (
            "",
            "ENCOUNTER BOUNDARY",
            "This preserved prescription is assignment intent/evidence, not proof that the saved build currently satisfies every encounter requirement or runtime uptime target.",
        )
    )
    return "\n".join(lines)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import roster_assignment_build_details_support as details

    original = details._details_text

    def details_with_prescription(page, slot) -> str:
        text = original(page, slot)
        service = getattr(page, "_roster_recruit_adoption_service", None)
        if service is None:
            return text
        plan = details._selected_generated_plan(page)
        if plan is None:
            return text
        evidence = service.prescription_evidence(plan.name, slot.slot_name)
        if not evidence:
            return text
        return text + "\n" + _format_prescription_evidence(evidence)

    details._details_text = details_with_prescription
    _INSTALLED = True
