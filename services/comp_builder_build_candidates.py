from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from models.build_model import PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge
from services.team_prescription_slot_constraints import build_gear_set_names
from services.team_prescription_template_catalog import (
    TeamPrescriptionTemplate,
    TeamPrescriptionTemplateCatalog,
)
from services.team_role_autofill import normalize_team_role


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


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


def _role_matches(build_role: str, chair_role: str) -> bool:
    build_normalized = normalize_team_role(build_role)
    chair_normalized = normalize_team_role(chair_role)
    return bool(build_normalized and chair_normalized and build_normalized == chair_normalized)


def _class_matches(build_class: str, chair_class: str) -> bool:
    requested = _clean(chair_class)
    if not requested or requested.casefold() == "any class":
        return True
    return _clean(build_class).casefold() == requested.casefold()


@dataclass(frozen=True)
class CompBuildCandidate:
    candidate_id: str
    name: str
    source_kind: str
    source_name: str
    source_url: str
    eso_class: str
    role: str
    gear_sets: tuple[str, ...]
    skills: tuple[str, ...]
    mundus: str
    complete_build: bool
    unresolved: tuple[str, ...]
    score: float
    score_reasons: tuple[str, ...]


class CompBuilderBuildCandidateService:
    """Merge saved builds and versioned reference templates for one raid chair.

    This layer deliberately does not manufacture missing build fields. A reference
    template remains partial when its source only establishes class/role, while a
    saved BFF build can contribute concrete gear and skill evidence. Ranking is a
    deterministic relevance score, not canonical combat optimization.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def candidates_for_chair(
        self,
        *,
        goal: str,
        slot_name: str,
        role: str,
        preferred_class: str,
        observed_gear_sets: Iterable[str] = (),
        observed_skills: Iterable[str] = (),
    ) -> tuple[CompBuildCandidate, ...]:
        candidates: list[CompBuildCandidate] = []
        candidates.extend(
            self._saved_build_candidates(
                role=role,
                preferred_class=preferred_class,
                observed_gear_sets=observed_gear_sets,
                observed_skills=observed_skills,
            )
        )
        candidates.extend(
            self._reference_candidates(
                goal=goal,
                slot_name=slot_name,
                role=role,
                preferred_class=preferred_class,
                observed_gear_sets=observed_gear_sets,
                observed_skills=observed_skills,
            )
        )
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    # Source precedence is intentional. A matching saved BFF build
                    # is concrete user-owned evidence and should surface before a
                    # published reference template. Relevance score ranks candidates
                    # within that source tier; it must not let a catalog slot bonus
                    # leapfrog an eligible saved build.
                    0 if item.source_kind == "saved_build" else 1,
                    -item.score,
                    item.name.casefold(),
                    item.candidate_id.casefold(),
                ),
            )
        )

    def _saved_build_candidates(
        self,
        *,
        role: str,
        preferred_class: str,
        observed_gear_sets: Iterable[str],
        observed_skills: Iterable[str],
    ) -> list[CompBuildCandidate]:
        roster = CanonicalBuildBridge(
            self.data_dir / "builds.json",
            self.data_dir / "characters.json",
        ).load()
        results: list[CompBuildCandidate] = []
        for index, build in enumerate(roster.Members):
            if not _role_matches(build.Role, role):
                continue
            if not _class_matches(build.EsoClass, preferred_class):
                continue
            score, reasons = self._relevance_score(
                build=build,
                preferred_class=preferred_class,
                observed_gear_sets=observed_gear_sets,
                observed_skills=observed_skills,
                base=80.0,
            )
            name = _clean(build.BuildName) or _clean(build.Name) or f"Saved build {index + 1}"
            identity = _clean(build.Name) or _clean(build.Gamertag) or "Saved character"
            results.append(
                CompBuildCandidate(
                    candidate_id=f"saved:{index}:{name}",
                    name=name,
                    source_kind="saved_build",
                    source_name=identity,
                    source_url="",
                    eso_class=_clean(build.EsoClass),
                    role=_clean(build.Role),
                    gear_sets=tuple(build_gear_set_names(build)),
                    skills=_known_skills(build),
                    mundus=_clean(build.Mundus),
                    complete_build=bool(
                        build_gear_set_names(build)
                        and _known_skills(build)
                        and _clean(build.EsoClass)
                        and normalize_team_role(build.Role)
                    ),
                    unresolved=(),
                    score=score,
                    score_reasons=reasons,
                )
            )
        return results

    def _reference_candidates(
        self,
        *,
        goal: str,
        slot_name: str,
        role: str,
        preferred_class: str,
        observed_gear_sets: Iterable[str],
        observed_skills: Iterable[str],
    ) -> list[CompBuildCandidate]:
        snapshot = TeamPrescriptionTemplateCatalog(
            self.data_dir / "team_prescription_templates.json"
        ).load()
        results: list[CompBuildCandidate] = []
        for template in snapshot.templates:
            if not template.supports_goal(goal):
                continue
            build = template.build
            if not _role_matches(build.Role, role):
                continue
            if not _class_matches(build.EsoClass, preferred_class):
                continue
            score, reasons = self._relevance_score(
                build=build,
                preferred_class=preferred_class,
                observed_gear_sets=observed_gear_sets,
                observed_skills=observed_skills,
                base=50.0 + template.score_for(goal=goal, slot_name=slot_name),
            )
            results.append(self._from_template(template, score=score, reasons=reasons))
        return results

    @staticmethod
    def _from_template(
        template: TeamPrescriptionTemplate,
        *,
        score: float,
        reasons: tuple[str, ...],
    ) -> CompBuildCandidate:
        build = template.build
        return CompBuildCandidate(
            candidate_id=f"template:{template.template_id}",
            name=template.name,
            source_kind="reference_template",
            source_name=template.source_name,
            source_url=template.source_url,
            eso_class=_clean(build.EsoClass),
            role=_clean(build.Role),
            gear_sets=tuple(build_gear_set_names(build)),
            skills=_known_skills(build),
            mundus=_clean(build.Mundus),
            complete_build=template.complete_build,
            unresolved=template.unresolved,
            score=score,
            score_reasons=reasons,
        )

    @staticmethod
    def _relevance_score(
        *,
        build: PlayerBuild,
        preferred_class: str,
        observed_gear_sets: Iterable[str],
        observed_skills: Iterable[str],
        base: float,
    ) -> tuple[float, tuple[str, ...]]:
        score = float(base)
        reasons: list[str] = []
        requested_class = _clean(preferred_class)
        if requested_class and requested_class.casefold() != "any class":
            if _clean(build.EsoClass).casefold() == requested_class.casefold():
                score += 25.0
                reasons.append(f"matches requested class {requested_class}")

        gear = {name.casefold() for name in build_gear_set_names(build) if _clean(name)}
        observed_gear = {_clean(name).casefold() for name in observed_gear_sets if _clean(name)}
        gear_overlap = sorted(gear & observed_gear)
        if gear_overlap:
            score += min(30.0, 10.0 * len(gear_overlap))
            reasons.append(f"{len(gear_overlap)} observed gear-set match(es)")

        skills = {name.casefold() for name in _known_skills(build)}
        observed_skill_names = {_clean(name).casefold() for name in observed_skills if _clean(name)}
        skill_overlap = sorted(skills & observed_skill_names)
        if skill_overlap:
            score += min(20.0, 2.0 * len(skill_overlap))
            reasons.append(f"{len(skill_overlap)} observed skill match(es)")

        if build_gear_set_names(build):
            score += 5.0
            reasons.append("contains concrete gear")
        if _known_skills(build):
            score += 5.0
            reasons.append("contains concrete skills")

        if not reasons:
            reasons.append("role/class catalog relevance only")
        return score, tuple(reasons)
