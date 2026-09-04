from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.team_prescription_observed_templates import ObservedTeamTemplateStore
from services.team_prescription_template_catalog import TeamPrescriptionTemplateCatalog
from services.team_role_autofill import normalize_team_role, slot_role_family
from services.team_prescription_slot_constraints import build_gear_set_names


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class TeamTemplateInspection:
    template_id: str
    name: str
    template_kind: str
    role: str
    eso_class: str
    complete_build: bool
    source_name: str
    source_url: str
    game_update: str
    retrieved_at: str
    catalog_version: str = ""
    trial_name: str = ""
    encounter_name: str = ""
    report_code: str = ""
    fight_id: int = 0
    observed_player_name: str = ""
    gear_sets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mundus: str = ""
    known_fields: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()


def _role_matches(slot_name: str, role: str) -> bool:
    try:
        required = slot_role_family(slot_name)
    except ValueError:
        return False
    return normalize_team_role(role) == required


def _published_inspection(template) -> TeamTemplateInspection:
    build = template.build
    gear_sets = build_gear_set_names(build)
    skills = tuple(
        value
        for value in (
            str(item or "").strip()
            for item in (*build.FrontBarSkills, *build.BackBarSkills)
        )
        if value
    )
    known: list[str] = ["class", "role"]
    if build.Race:
        known.append("race")
    if gear_sets:
        known.append("gear sets")
    if skills:
        known.append("skills")
    if build.Mundus:
        known.append("mundus")
    if build.ChampionPoints:
        known.append("champion points")
    if build.Food:
        known.append("food")
    if build.Potion:
        known.append("potion")
    return TeamTemplateInspection(
        template_id=template.template_id,
        name=template.name,
        template_kind="Published reference template",
        role=build.Role,
        eso_class=build.EsoClass,
        complete_build=template.complete_build,
        source_name=template.source_name,
        source_url=template.source_url,
        game_update=template.game_update,
        retrieved_at=template.retrieved_at,
        catalog_version=template.catalog_version,
        gear_sets=gear_sets,
        skills=skills,
        mundus=build.Mundus,
        known_fields=tuple(known),
        unknown_fields=tuple(template.unresolved),
    )


def _observed_inspection(template) -> TeamTemplateInspection:
    known: list[str] = ["class", "role"]
    if template.gear_sets:
        known.append("gear sets")
    if template.skills:
        known.append("skills")
    if template.mundus:
        known.append("mundus")
    return TeamTemplateInspection(
        template_id=template.template_id,
        name=template.name,
        template_kind="Observed performance template",
        role=template.role,
        eso_class=template.eso_class,
        complete_build=False,
        source_name=template.source_name,
        source_url=template.source_url,
        game_update=template.game_update,
        retrieved_at=template.retrieved_at,
        trial_name=template.trial_name,
        encounter_name=template.encounter_name,
        report_code=template.report_code,
        fight_id=template.fight_id,
        observed_player_name=template.observed_player_name,
        gear_sets=template.gear_sets,
        skills=template.skills,
        mundus=template.mundus,
        known_fields=tuple(known),
        unknown_fields=template.unknown_fields,
    )


def find_team_template_inspection(
    *,
    data_dir: str | Path,
    slot_name: str,
    build_name: str,
    eso_class: str = "",
) -> TeamTemplateInspection | None:
    """Resolve a generated recruit row back to its template evidence.

    Matching is deliberately deterministic: exact build/template name, compatible
    slot role, and (when supplied) exact class. Published templates are checked
    before user-curated observed templates because the prescription pipeline applies
    them in that same source-priority order.
    """

    target_name = _clean(build_name).casefold()
    target_class = _clean(eso_class).casefold()
    if not target_name or target_name in {"open requirement", "partial template"}:
        return None

    root = Path(data_dir)
    published = TeamPrescriptionTemplateCatalog(
        root / "team_prescription_templates.json"
    ).load()
    for template in published.templates:
        build = template.build
        names = {
            _clean(template.name).casefold(),
            _clean(build.BuildName).casefold(),
        }
        if target_name not in names:
            continue
        if not _role_matches(slot_name, build.Role):
            continue
        if target_class and _clean(build.EsoClass).casefold() != target_class:
            continue
        return _published_inspection(template)

    observed = ObservedTeamTemplateStore(
        root / "team_prescription_observed_templates.json"
    ).load()
    for template in observed.templates:
        if target_name != _clean(template.name).casefold():
            continue
        if not _role_matches(slot_name, template.role):
            continue
        if target_class and _clean(template.eso_class).casefold() != target_class:
            continue
        return _observed_inspection(template)

    return None
