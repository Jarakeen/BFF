from __future__ import annotations

import json
from pathlib import Path

from services.canonical_build_bridge import CanonicalBuildBridge
from services.comp_builder_build_candidates import CompBuildCandidate
from services.team_prescription import (
    PrescribedBuildChange,
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_template_catalog import TeamPrescriptionTemplateCatalog


_DEFAULT_SCOPE = TeamPrescriptionScope(
    dimensions=(
        PrescriptionDimension.ROLE,
        PrescriptionDimension.CLASS,
        PrescriptionDimension.RACE,
        PrescriptionDimension.BUILD,
        PrescriptionDimension.GEAR,
        PrescriptionDimension.SKILLS,
        PrescriptionDimension.MORPHS,
        PrescriptionDimension.CHAMPION_POINTS,
        PrescriptionDimension.MUNDUS,
        PrescriptionDimension.FOOD,
        PrescriptionDimension.POTION,
    )
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _build_json(build) -> str:
    return json.dumps(
        build.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _change(
    *,
    dimension: PrescriptionDimension,
    value: str,
    candidate: CompBuildCandidate,
) -> PrescribedBuildChange | None:
    normalized = _clean(value)
    if not normalized:
        return None
    return PrescribedBuildChange(
        dimension=dimension,
        current_value=None,
        prescribed_value=normalized,
        reason=(
            f"Comp Maker whole-team optimizer selected {candidate.name!r} "
            f"({candidate.candidate_id})."
        ),
    )


class CompBuilderAuthoritativePrescriptionService:
    """Materialize Comp Maker choices without reranking them.

    The whole-team optimizer owns candidate selection. This service only resolves the
    already-selected candidate IDs back to their exact saved/template source snapshots
    and emits the existing non-destructive PrescribedRoster model.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def materialize(
        self,
        *,
        name: str,
        goal: str,
        slots: tuple[tuple[str, str], ...],
        candidates_by_slot: dict[str, CompBuildCandidate],
        scope: TeamPrescriptionScope = _DEFAULT_SCOPE,
    ) -> PrescribedRoster:
        saved = CanonicalBuildBridge(
            self.data_dir / "builds.json",
            self.data_dir / "characters.json",
        ).load().Members
        templates = TeamPrescriptionTemplateCatalog(
            self.data_dir / "team_prescription_templates.json"
        ).load().templates
        templates_by_id = {template.template_id: template for template in templates}

        assignments: list[PrescribedRosterAssignment] = []
        unresolved: list[str] = []
        assumptions: list[str] = [
            "Comp Maker whole-team optimizer assignments are authoritative; materialization does not rerank candidates."
        ]

        for slot_name, role in slots:
            candidate = candidates_by_slot.get(slot_name)
            if candidate is None:
                detail = f"{slot_name}: no authoritative Comp Maker candidate was selected"
                assignments.append(
                    PrescribedRosterAssignment(
                        slot_name=slot_name,
                        player_name=None,
                        source_build_name=None,
                        prescribed_role=role,
                        unresolved=(detail,),
                    )
                )
                unresolved.append(detail)
                continue

            if candidate.source_kind == "saved_build":
                assignments.append(
                    self._saved_assignment(
                        slot_name=slot_name,
                        role=role,
                        candidate=candidate,
                        saved_builds=saved,
                    )
                )
                continue

            if candidate.source_kind == "reference_template":
                assignment, notes = self._template_assignment(
                    slot_name=slot_name,
                    role=role,
                    candidate=candidate,
                    templates_by_id=templates_by_id,
                )
                assignments.append(assignment)
                unresolved.extend(notes)
                continue

            detail = (
                f"{slot_name}: unsupported authoritative candidate source "
                f"{candidate.source_kind!r} for {candidate.candidate_id}"
            )
            assignments.append(
                PrescribedRosterAssignment(
                    slot_name=slot_name,
                    player_name=None,
                    source_build_name=candidate.name or None,
                    prescribed_role=role,
                    unresolved=(detail,),
                )
            )
            unresolved.append(detail)

        return PrescribedRoster(
            name=name,
            goal=goal,
            scope=scope,
            assignments=tuple(assignments),
            assumptions=tuple(assumptions),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _saved_assignment(*, slot_name, role, candidate, saved_builds):
        parts = candidate.candidate_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "saved":
            raise ValueError(f"invalid saved Comp Maker candidate id: {candidate.candidate_id}")
        try:
            index = int(parts[1])
        except ValueError as exc:
            raise ValueError(
                f"invalid saved Comp Maker candidate index: {candidate.candidate_id}"
            ) from exc
        if not 0 <= index < len(saved_builds):
            raise ValueError(f"stale saved Comp Maker candidate: {candidate.candidate_id}")

        build = saved_builds[index]
        build_name = _clean(build.BuildName) or _clean(build.Name)
        owner = _clean(build.Name) or _clean(build.Gamertag)
        if build_name.casefold() != _clean(candidate.name).casefold():
            raise ValueError(f"stale saved Comp Maker candidate name: {candidate.candidate_id}")
        if owner.casefold() != _clean(candidate.source_name).casefold():
            raise ValueError(f"stale saved Comp Maker candidate owner: {candidate.candidate_id}")

        return PrescribedRosterAssignment(
            slot_name=slot_name,
            player_name=owner or None,
            source_build_name=build_name or None,
            prescribed_role=role,
            prescribed_build_json=_build_json(build),
        )

    @staticmethod
    def _template_assignment(*, slot_name, role, candidate, templates_by_id):
        prefix = "template:"
        if not candidate.candidate_id.startswith(prefix):
            raise ValueError(f"invalid template Comp Maker candidate id: {candidate.candidate_id}")
        template_id = candidate.candidate_id[len(prefix):]
        template = templates_by_id.get(template_id)
        if template is None:
            raise ValueError(f"stale template Comp Maker candidate: {candidate.candidate_id}")
        if template.name.casefold() != _clean(candidate.name).casefold():
            raise ValueError(f"stale template Comp Maker candidate name: {candidate.candidate_id}")

        build = template.build
        if template.complete_build:
            return (
                PrescribedRosterAssignment(
                    slot_name=slot_name,
                    player_name=None,
                    source_build_name=template.name,
                    prescribed_role=role,
                    prescribed_build_json=_build_json(build),
                ),
                (),
            )

        proposed = (
            _change(dimension=PrescriptionDimension.CLASS, value=build.EsoClass, candidate=candidate),
            _change(dimension=PrescriptionDimension.BUILD, value=build.BuildName or template.name, candidate=candidate),
            _change(dimension=PrescriptionDimension.GEAR, value=" + ".join(candidate.gear_sets), candidate=candidate),
            _change(dimension=PrescriptionDimension.SKILLS, value=" / ".join(candidate.skills), candidate=candidate),
            _change(dimension=PrescriptionDimension.MUNDUS, value=candidate.mundus, candidate=candidate),
        )
        changes = tuple(change for change in proposed if change is not None)
        detail = (
            f"{slot_name}: {template.name} is partial reference evidence; "
            "missing fields remain unresolved"
        )
        unresolved = tuple(dict.fromkeys((*candidate.unresolved, detail)))
        return (
            PrescribedRosterAssignment(
                slot_name=slot_name,
                player_name=None,
                source_build_name=template.name,
                prescribed_role=role,
                changes=changes,
                unresolved=unresolved,
                prescribed_build_json=None,
            ),
            unresolved,
        )
