from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription_candidate_source import (
    PrescribedObjectiveMeasurement,
    PrescribedOpenSlotCandidate,
)
from services.team_prescription_slot_constraints import build_gear_set_names
from services.team_role_autofill import normalize_team_role


CATALOG_SCHEMA_VERSION = 1


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _score_map(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, raw_score in value.items():
        name = _clean(key)
        if not name:
            continue
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            continue
        result[name.casefold()] = score
    return result


def _display_goal_name(value: object) -> str:
    """Render normalized catalog goal keys as readable achievement names."""

    return _clean(value).title()


def _known_skills(build: PlayerBuild) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for raw in (*build.FrontBarSkills, *build.BackBarSkills):
        text = _clean(raw)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            values.append(text)
    return tuple(values)


@dataclass(frozen=True)
class TeamPrescriptionTemplate:
    template_id: str
    name: str
    catalog_version: str
    game_update: str
    source_name: str
    source_url: str
    retrieved_at: str
    base_score: float
    slot_scores: dict[str, float]
    goal_scores: dict[str, float]
    build_json: str
    complete_build: bool = False
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "template_id",
            "name",
            "catalog_version",
            "game_update",
            "source_name",
            "source_url",
        ):
            if not _clean(getattr(self, field_name)):
                raise ValueError(f"team prescription template requires {field_name}")
        try:
            payload = json.loads(self.build_json)
        except json.JSONDecodeError as exc:
            raise ValueError("team prescription template contains invalid build JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("team prescription template build must be a JSON object")
        build = PlayerBuild.from_dict(payload)
        if normalize_team_role(build.Role) is None:
            raise ValueError(
                f"team prescription template {self.template_id!r} has unsupported role {build.Role!r}"
            )
        if not _clean(build.EsoClass):
            raise ValueError(
                f"team prescription template {self.template_id!r} requires an ESO class"
            )

    @property
    def build(self) -> PlayerBuild:
        return PlayerBuild.from_dict(json.loads(self.build_json))

    def supports_goal(self, goal: str) -> bool:
        """Return whether this template is eligible for the requested goal.

        Empty ``goal_scores`` means the template is intentionally generic. Once a
        template declares one or more goal-specific scores, those keys become an
        allow-list rather than optional bonuses. This prevents a Sunspire/Godslayer
        reference from leaking into Swashbuckler Supreme merely because it has a
        positive base score.
        """

        if not self.goal_scores:
            return True
        return _clean(goal).casefold() in self.goal_scores

    def score_for(self, *, goal: str, slot_name: str) -> float:
        score = float(self.base_score)
        score += self.slot_scores.get(_clean(slot_name).casefold(), 0.0)
        score += self.goal_scores.get(_clean(goal).casefold(), 0.0)
        return score

    def to_candidate(self) -> PrescribedOpenSlotCandidate:
        build = self.build
        metadata = {
            "complete_build": bool(self.complete_build),
            "template_kind": "published_reference_template",
            "observed_class": build.EsoClass,
            "observed_gear_sets": list(build_gear_set_names(build)),
            "observed_skills": list(_known_skills(build)),
            "observed_mundus": build.Mundus,
            "unknown_fields": list(self.unresolved),
            "source_name": self.source_name,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "game_update": self.game_update,
            "catalog_version": self.catalog_version,
            "supported_goals": [
                _display_goal_name(goal_name) for goal_name in self.goal_scores.keys()
            ],
        }
        return PrescribedOpenSlotCandidate.from_build(
            candidate_id=self.template_id,
            candidate_build=build,
            candidate_source=(
                f"{self.source_name} | {self.catalog_version} | {self.game_update}"
            ),
            candidate_metadata=metadata,
        )


@dataclass(frozen=True)
class TeamPrescriptionTemplateCatalogSnapshot:
    schema_version: int
    catalog_version: str
    game_update: str
    templates: tuple[TeamPrescriptionTemplate, ...]


class TeamPrescriptionTemplateCatalog:
    """Load immutable, provenance-bearing open-chair recommendation templates.

    Templates are candidate-generation evidence, not canonical ESO math. They are
    deliberately ranked by an explicit catalog/source score only after the canonical
    saved-player candidate pass has had the opportunity to fill a chair.

    ``complete_build`` is an explicit catalog declaration. Merely deserializing into
    ``PlayerBuild`` does not make a reference setup complete because model defaults can
    legitimately leave race, gear, traits, CP, food, potion, or bars empty. Only a
    template intentionally marked complete may become a saveable prescribed snapshot.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> TeamPrescriptionTemplateCatalogSnapshot:
        if not self.path.is_file():
            return TeamPrescriptionTemplateCatalogSnapshot(
                schema_version=CATALOG_SCHEMA_VERSION,
                catalog_version="missing",
                game_update="unresolved",
                templates=(),
            )
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("team prescription template catalog must be a JSON object")
        schema_version = int(raw.get("schema_version", 0))
        if schema_version != CATALOG_SCHEMA_VERSION:
            raise ValueError(
                "unsupported team prescription template catalog schema: "
                f"{schema_version}"
            )
        catalog_version = _clean(raw.get("catalog_version"))
        game_update = _clean(raw.get("game_update"))
        if not catalog_version or not game_update:
            raise ValueError("team prescription template catalog requires version metadata")

        templates: list[TeamPrescriptionTemplate] = []
        seen: set[str] = set()
        for raw_template in raw.get("templates") or ():
            if not isinstance(raw_template, dict):
                continue
            template_id = _clean(raw_template.get("template_id"))
            key = template_id.casefold()
            if not template_id:
                raise ValueError("team prescription template_id is required")
            if key in seen:
                raise ValueError(f"duplicate team prescription template_id: {template_id}")
            seen.add(key)
            build_payload = raw_template.get("build")
            if not isinstance(build_payload, dict):
                raise ValueError(
                    f"team prescription template {template_id!r} requires build object"
                )
            templates.append(
                TeamPrescriptionTemplate(
                    template_id=template_id,
                    name=_clean(raw_template.get("name")) or template_id,
                    catalog_version=catalog_version,
                    game_update=game_update,
                    source_name=_clean(raw_template.get("source_name")),
                    source_url=_clean(raw_template.get("source_url")),
                    retrieved_at=_clean(raw_template.get("retrieved_at")),
                    base_score=float(raw_template.get("base_score", 0.0)),
                    slot_scores=_score_map(raw_template.get("slot_scores")),
                    goal_scores=_score_map(raw_template.get("goal_scores")),
                    build_json=json.dumps(
                        build_payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    complete_build=bool(raw_template.get("complete_build", False)),
                    unresolved=tuple(
                        _clean(item)
                        for item in (raw_template.get("unresolved") or ())
                        if _clean(item)
                    ),
                )
            )
        return TeamPrescriptionTemplateCatalogSnapshot(
            schema_version=schema_version,
            catalog_version=catalog_version,
            game_update=game_update,
            templates=tuple(templates),
        )


class TemplateCatalogObjectiveEvaluator:
    """Rank catalog templates using explicit source/catalog evidence only."""

    def __init__(
        self,
        snapshot: TeamPrescriptionTemplateCatalogSnapshot,
        *,
        goal: str,
    ) -> None:
        self.snapshot = snapshot
        self.goal = _clean(goal)
        self._by_id = {template.template_id: template for template in snapshot.templates}

    def __call__(
        self,
        candidate: PrescribedOpenSlotCandidate,
        slot_name: str,
    ) -> PrescribedObjectiveMeasurement:
        template = self._by_id.get(candidate.candidate_id)
        if template is None:
            raise ValueError(f"template catalog has no candidate {candidate.candidate_id!r}")
        role = normalize_team_role(candidate.candidate_build.Role)
        objective = {
            "dd": EvaluationObjective.DAMAGE,
            "healer": EvaluationObjective.HEALING,
            "tank": EvaluationObjective.SURVIVABILITY,
        }[role]

        if not template.supports_goal(self.goal):
            supported = ", ".join(
                _display_goal_name(goal_name) for goal_name in template.goal_scores.keys()
            ) or "Generic"
            return PrescribedObjectiveMeasurement(
                objective=objective,
                value=None,
                metric_name="versioned reference-template score",
                constraints=(),
                evidence=(
                    f"template={template.template_id}",
                    f"requested_goal={self.goal or 'unresolved'}",
                    f"supported_goals={supported}",
                ),
                rejection_reason=(
                    f"template {template.template_id!r} is scoped to {supported} and "
                    f"cannot be used for {self.goal or 'an unresolved goal'}"
                ),
            )

        score = template.score_for(goal=self.goal, slot_name=slot_name)
        evidence = (
            f"template={template.template_id}",
            f"catalog={template.catalog_version}",
            f"game_update={template.game_update}",
            f"source={template.source_name}",
            f"source_url={template.source_url}",
            f"retrieved_at={template.retrieved_at or 'unresolved'}",
            f"complete_build={str(template.complete_build).lower()}",
            "boundary=reference-template source score; not canonical damage/HPS/tank math",
            *tuple(f"template limitation: {item}" for item in template.unresolved),
        )
        return PrescribedObjectiveMeasurement(
            objective=objective,
            value=score,
            metric_name="versioned reference-template score",
            constraints=(),
            evidence=evidence,
        )


def catalog_candidates(
    snapshot: TeamPrescriptionTemplateCatalogSnapshot,
) -> tuple[PrescribedOpenSlotCandidate, ...]:
    return tuple(template.to_candidate() for template in snapshot.templates)


def template_by_candidate_id(
    snapshot: TeamPrescriptionTemplateCatalogSnapshot,
    candidate_id: str,
) -> TeamPrescriptionTemplate | None:
    return next(
        (
            template
            for template in snapshot.templates
            if template.template_id == candidate_id
        ),
        None,
    )
