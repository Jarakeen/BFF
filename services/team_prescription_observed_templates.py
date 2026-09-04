from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from minmax.build_candidate_comparison import CandidateConstraint
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription_candidate_source import (
    PrescribedObjectiveMeasurement,
    PrescribedOpenSlotCandidate,
)
from services.team_role_autofill import normalize_team_role


OBSERVED_TEMPLATE_SCHEMA_VERSION = 1


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _dedupe_strings(values: Iterable[object]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            value = (
                value.get("name")
                or value.get("displayName")
                or value.get("setName")
                or value.get("abilityName")
                or ""
            )
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return tuple(result)


def _iterable_attr(value: object, *names: str) -> tuple[object, ...]:
    for name in names:
        raw = getattr(value, name, None)
        if isinstance(raw, (list, tuple, set)):
            return tuple(raw)
        if isinstance(value, dict):
            raw = value.get(name)
            if isinstance(raw, (list, tuple, set)):
                return tuple(raw)
    return ()


def _scalar_attr(value: object, *names: str) -> str:
    for name in names:
        raw = getattr(value, name, None)
        if raw is None and isinstance(value, dict):
            raw = value.get(name)
        text = _clean(raw)
        if text:
            return text
    return ""


def _role_label(value: str) -> str:
    normalized = normalize_team_role(value)
    return {"tank": "Tank", "healer": "Healer", "dd": "DD"}.get(
        normalized or "",
        value,
    )


def _default_unknown_fields(
    *,
    gear_sets: tuple[str, ...],
    skills: tuple[str, ...],
    mundus: str,
) -> tuple[str, ...]:
    unknown = [
        "race",
        "attributes",
        "gear slot placement",
        "traits",
        "enchants",
        "champion points",
        "food",
        "potion",
    ]
    if not gear_sets:
        unknown.append("gear sets")
    if skills:
        unknown.append("skill bar placement")
    else:
        unknown.append("skills")
    if not mundus:
        unknown.append("mundus")
    return tuple(unknown)


@dataclass(frozen=True)
class ObservedTeamTemplate:
    """One curated, partial build observation from an external performance source.

    This record intentionally does not claim to be a complete ``PlayerBuild``. It
    preserves exactly what was observed and records the important missing fields.
    """

    template_id: str
    name: str
    source_name: str
    source_url: str
    retrieved_at: str
    game_update: str
    trial_name: str
    encounter_name: str
    report_code: str
    fight_id: int
    observed_player_name: str
    role: str
    eso_class: str
    gear_sets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mundus: str = ""
    unknown_fields: tuple[str, ...] = ()
    source_score: float = 100.0

    def __post_init__(self) -> None:
        template_id = _clean(self.template_id)
        name = _clean(self.name)
        source_name = _clean(self.source_name)
        role = _role_label(_clean(self.role))
        eso_class = _clean(self.eso_class)
        if not template_id or not name or not source_name:
            raise ValueError("observed team template requires id, name, and source")
        if normalize_team_role(role) is None:
            raise ValueError(f"unsupported observed template role: {self.role!r}")
        if not eso_class:
            raise ValueError("observed team template requires an ESO class")
        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "eso_class", eso_class)
        object.__setattr__(self, "gear_sets", _dedupe_strings(self.gear_sets))
        object.__setattr__(self, "skills", _dedupe_strings(self.skills))
        object.__setattr__(self, "unknown_fields", _dedupe_strings(self.unknown_fields))
        if float(self.source_score) < 0:
            raise ValueError("observed template source score cannot be negative")

    def to_candidate(self) -> PrescribedOpenSlotCandidate:
        # Only fields that are actually known as build fields are projected. Gear
        # set names and unbarred skills remain metadata because assigning them to an
        # arbitrary slot/bar would manufacture detail that ESO Logs did not prove.
        build = PlayerBuild(
            BuildName=self.name,
            EsoClass=self.eso_class,
            Role=self.role,
            Mundus=self.mundus,
        )
        metadata = {
            "complete_build": False,
            "template_kind": "observed_performance_setup",
            "observed_class": self.eso_class,
            "observed_gear_sets": list(self.gear_sets),
            "observed_skills": list(self.skills),
            "observed_mundus": self.mundus,
            "unknown_fields": list(self.unknown_fields),
            "source_name": self.source_name,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "game_update": self.game_update,
            "trial_name": self.trial_name,
            "encounter_name": self.encounter_name,
            "report_code": self.report_code,
            "fight_id": self.fight_id,
            "observed_player_name": self.observed_player_name,
            "source_score": float(self.source_score),
        }
        return PrescribedOpenSlotCandidate.from_build(
            candidate_id=self.template_id,
            candidate_build=build,
            candidate_source=(
                f"{self.source_name} | {self.game_update or 'update unresolved'} | "
                f"{self.encounter_name or self.trial_name or 'encounter unresolved'}"
            ),
            candidate_metadata=metadata,
        )


@dataclass(frozen=True)
class ObservedTeamTemplateSnapshot:
    schema_version: int
    templates: tuple[ObservedTeamTemplate, ...]


class ObservedTeamTemplateStore:
    """Persist user-curated performance observations without mutating saved builds."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> ObservedTeamTemplateSnapshot:
        if not self.path.is_file():
            return ObservedTeamTemplateSnapshot(
                schema_version=OBSERVED_TEMPLATE_SCHEMA_VERSION,
                templates=(),
            )
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("observed team template store must be a JSON object")
        schema_version = int(raw.get("schema_version", 0))
        if schema_version != OBSERVED_TEMPLATE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported observed team template schema: {schema_version}"
            )
        templates: list[ObservedTeamTemplate] = []
        seen: set[str] = set()
        for item in raw.get("templates") or ():
            if not isinstance(item, dict):
                continue
            record = ObservedTeamTemplate(
                template_id=item.get("template_id", ""),
                name=item.get("name", ""),
                source_name=item.get("source_name", ""),
                source_url=item.get("source_url", ""),
                retrieved_at=item.get("retrieved_at", ""),
                game_update=item.get("game_update", ""),
                trial_name=item.get("trial_name", ""),
                encounter_name=item.get("encounter_name", ""),
                report_code=item.get("report_code", ""),
                fight_id=int(item.get("fight_id", 0) or 0),
                observed_player_name=item.get("observed_player_name", ""),
                role=item.get("role", ""),
                eso_class=item.get("eso_class", ""),
                gear_sets=tuple(item.get("gear_sets") or ()),
                skills=tuple(item.get("skills") or ()),
                mundus=item.get("mundus", ""),
                unknown_fields=tuple(item.get("unknown_fields") or ()),
                source_score=float(item.get("source_score", 100.0)),
            )
            key = record.template_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate observed team template id: {record.template_id}"
                )
            seen.add(key)
            templates.append(record)
        return ObservedTeamTemplateSnapshot(
            schema_version=schema_version,
            templates=tuple(templates),
        )

    def save(self, snapshot: ObservedTeamTemplateSnapshot) -> None:
        payload = {
            "schema_version": OBSERVED_TEMPLATE_SCHEMA_VERSION,
            "templates": [asdict(template) for template in snapshot.templates],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def upsert(self, template: ObservedTeamTemplate) -> ObservedTeamTemplate:
        snapshot = self.load()
        rows = list(snapshot.templates)
        key = template.template_id.casefold()
        for index, existing in enumerate(rows):
            if existing.template_id.casefold() == key:
                rows[index] = template
                break
        else:
            rows.append(template)
        self.save(
            ObservedTeamTemplateSnapshot(
                schema_version=OBSERVED_TEMPLATE_SCHEMA_VERSION,
                templates=tuple(rows),
            )
        )
        return template

    def add_top_team_player(
        self,
        *,
        result: object,
        player: object,
        game_update: str = "unresolved",
        retrieved_at: str | None = None,
        source_score: float = 100.0,
    ) -> ObservedTeamTemplate:
        """Curate one player setup from either old or new Top Team result shapes.

        The adapter intentionally uses a tolerant read boundary because the
        Performance UI is being evolved independently. Missing fields remain missing;
        this method never fabricates gear slots, bar positions, traits, or CP.
        """

        trial_name = _scalar_attr(result, "TrialName", "trial_name")
        encounter_name = _scalar_attr(result, "EncounterName", "encounter_name")
        report_code = _scalar_attr(result, "ReportCode", "report_code")
        raw_fight = getattr(result, "FightId", None)
        if raw_fight is None and isinstance(result, dict):
            raw_fight = result.get("FightId", result.get("fight_id", 0))
        fight_id = int(raw_fight or 0)

        player_name = _scalar_attr(player, "Name", "name", "displayName")
        role = _scalar_attr(player, "Role", "role")
        eso_class = _scalar_attr(
            player,
            "EsoClass",
            "ClassName",
            "Class",
            "class_name",
            "type",
        )
        gear_sets = _dedupe_strings(
            _iterable_attr(player, "GearSets", "gear_sets", "sets")
        )
        skills = _dedupe_strings(
            _iterable_attr(player, "Skills", "Abilities", "skills", "abilities")
        )
        mundus = _scalar_attr(player, "Mundus", "mundus")
        if normalize_team_role(role) is None:
            raise ValueError(f"cannot template unsupported player role: {role!r}")
        if not eso_class:
            raise ValueError("cannot template ESO Logs setup without a resolved class")

        source_url = (
            f"https://www.esologs.com/reports/{report_code}" if report_code else "https://www.esologs.com/"
        )
        identity = "|".join(
            (
                "esologs",
                report_code,
                str(fight_id),
                player_name.casefold(),
                role.casefold(),
                eso_class.casefold(),
            )
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        role_label = _role_label(role)
        encounter_label = encounter_name or trial_name or "Observed Encounter"
        name = f"{eso_class} {role_label} — {encounter_label}"
        record = ObservedTeamTemplate(
            template_id=f"esologs:{digest}",
            name=name,
            source_name="ESO Logs",
            source_url=source_url,
            retrieved_at=(
                retrieved_at
                or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            ),
            game_update=_clean(game_update) or "unresolved",
            trial_name=trial_name,
            encounter_name=encounter_name,
            report_code=report_code,
            fight_id=fight_id,
            observed_player_name=player_name,
            role=role_label,
            eso_class=eso_class,
            gear_sets=gear_sets,
            skills=skills,
            mundus=mundus,
            unknown_fields=_default_unknown_fields(
                gear_sets=gear_sets,
                skills=skills,
                mundus=mundus,
            ),
            source_score=float(source_score),
        )
        return self.upsert(record)


class ObservedTemplateObjectiveEvaluator:
    """Rank observed templates by explicit source evidence, never hidden ESO math."""

    def __init__(self, snapshot: ObservedTeamTemplateSnapshot):
        self._by_id = {
            template.template_id: template for template in snapshot.templates
        }

    def __call__(
        self,
        candidate: PrescribedOpenSlotCandidate,
        slot_name: str,
    ) -> PrescribedObjectiveMeasurement:
        template = self._by_id.get(candidate.candidate_id)
        if template is None:
            raise ValueError(
                f"observed template store has no candidate {candidate.candidate_id!r}"
            )
        role = normalize_team_role(template.role)
        objective = {
            "dd": EvaluationObjective.DAMAGE,
            "healer": EvaluationObjective.HEALING,
            "tank": EvaluationObjective.SURVIVABILITY,
        }[role]
        evidence = (
            f"template={template.template_id}",
            f"source={template.source_name}",
            f"source_url={template.source_url}",
            f"trial={template.trial_name or 'unresolved'}",
            f"encounter={template.encounter_name or 'unresolved'}",
            f"report={template.report_code or 'unresolved'}",
            f"fight={template.fight_id}",
            f"game_update={template.game_update}",
            f"retrieved_at={template.retrieved_at}",
            "boundary=observed performance-template score; not canonical damage/HPS/tank math",
        )
        return PrescribedObjectiveMeasurement(
            objective=objective,
            value=float(template.source_score),
            metric_name="observed performance-template score",
            constraints=tuple[CandidateConstraint, ...](),
            evidence=evidence,
        )


def observed_template_candidates(
    snapshot: ObservedTeamTemplateSnapshot,
) -> tuple[PrescribedOpenSlotCandidate, ...]:
    return tuple(template.to_candidate() for template in snapshot.templates)
