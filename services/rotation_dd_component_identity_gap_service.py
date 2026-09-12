from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_component_text_evidence import (
    SkillComponentTextEvidence,
    extract_component_text_evidence,
)
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class RotationDDComponentIdentityGapRow:
    """One coefficient-level DD component identity comparison."""

    bar: str
    slot: int
    skill_name: str
    skill_rank_id: int
    ability_id: int
    coefficient_number: int
    canonical_effect_kind: SkillEffectKind
    canonical_damage_type: str | None
    canonical_is_dot: bool | None
    canonical_is_aoe: bool | None
    text_evidence: SkillComponentTextEvidence

    @property
    def text_proves_damage(self) -> bool:
        return self.text_evidence.effect_kind == "damage"

    @property
    def text_proves_periodic_damage(self) -> bool:
        return self.text_proves_damage and self.text_evidence.is_dot is True

    @property
    def canonical_proves_damage(self) -> bool:
        return self.canonical_effect_kind is SkillEffectKind.DAMAGE

    @property
    def canonical_proves_periodic_damage(self) -> bool:
        return self.canonical_proves_damage and self.canonical_is_dot is True

    @property
    def needs_damage_identity_review(self) -> bool:
        return self.text_proves_damage and not self.canonical_proves_damage

    @property
    def needs_periodic_identity_review(self) -> bool:
        return self.text_proves_periodic_damage and not self.canonical_proves_periodic_damage


@dataclass(frozen=True)
class RotationDDComponentIdentityGapReport:
    character_name: str
    build_name: str
    rows: tuple[RotationDDComponentIdentityGapRow, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def review_candidates(self) -> tuple[RotationDDComponentIdentityGapRow, ...]:
        return tuple(
            row
            for row in self.rows
            if row.needs_damage_identity_review or row.needs_periodic_identity_review
        )


class RotationDDComponentIdentityGapService:
    """Compare coefficient-local damage text with persisted DD component identity.

    This is a read-only audit service. Coefficient text may identify review
    candidates, but it never writes or silently promotes canonical classification.
    That keeps Rotation Builder execution fail-closed while exposing exact
    skill-rank/coefficient coordinates for missing DD damage/periodic identities.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        component_repository: SkillComponentRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.components = component_repository or SkillComponentRepository(
            self.database_path
        )

    def inspect(self, build: PlayerBuild) -> RotationDDComponentIdentityGapReport:
        rows: list[RotationDDComponentIdentityGapRow] = []
        unresolved: list[str] = []

        for bar, skills in (
            ("front", tuple(getattr(build, "FrontBarSkills", ()) or ())),
            ("back", tuple(getattr(build, "BackBarSkills", ()) or ())),
        ):
            for slot, raw_name in enumerate(skills, start=1):
                skill_name = str(raw_name or "").strip()
                if not skill_name:
                    continue

                resolution = self.coefficients.resolve_name(skill_name)
                if resolution.rank is None:
                    messages = resolution.unresolved or (
                        f"canonical skill identity unresolved for {skill_name}",
                    )
                    unresolved.extend(
                        f"{bar} slot {slot} {skill_name}: {message}"
                        for message in messages
                    )
                    continue

                rank = resolution.rank
                description = self._coef_description(rank.ability_id)
                if not description:
                    unresolved.append(
                        f"{bar} slot {slot} {rank.name}: coef_description unavailable for DD component identity audit"
                    )
                    continue

                canonical_by_number = {
                    int(component.coefficient_number): component
                    for component in self.components.get_for_skill_rank(rank.skill_rank_id)
                }

                for coefficient in rank.coefficients:
                    number = int(coefficient.coefficient_number)
                    text = extract_component_text_evidence(description, number)
                    canonical = canonical_by_number.get(number)
                    canonical_kind = (
                        canonical.effect_kind
                        if canonical is not None
                        else SkillEffectKind.UNKNOWN
                    )

                    if (
                        canonical_kind is not SkillEffectKind.DAMAGE
                        and text.effect_kind != "damage"
                    ):
                        continue

                    rows.append(
                        RotationDDComponentIdentityGapRow(
                            bar=bar,
                            slot=slot,
                            skill_name=rank.name,
                            skill_rank_id=rank.skill_rank_id,
                            ability_id=rank.ability_id,
                            coefficient_number=number,
                            canonical_effect_kind=canonical_kind,
                            canonical_damage_type=(
                                canonical.damage_type if canonical is not None else None
                            ),
                            canonical_is_dot=(
                                canonical.is_dot if canonical is not None else None
                            ),
                            canonical_is_aoe=(
                                canonical.is_aoe if canonical is not None else None
                            ),
                            text_evidence=text,
                        )
                    )

        return RotationDDComponentIdentityGapReport(
            character_name=str(getattr(build, "Name", "") or "").strip(),
            build_name=str(getattr(build, "BuildName", "") or "").strip(),
            rows=tuple(rows),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _coef_description(self, ability_id: int) -> str:
        if not self.database_path.exists():
            return ""
        try:
            with sqlite3.connect(self.database_path) as db:
                columns = {
                    str(row[1])
                    for row in db.execute("PRAGMA table_info(ability)").fetchall()
                }
                if not {"ability_id", "coef_description"}.issubset(columns):
                    return ""
                row = db.execute(
                    "SELECT coef_description FROM ability WHERE ability_id = ?",
                    (int(ability_id),),
                ).fetchone()
        except sqlite3.Error:
            return ""
        if row is None or row[0] is None:
            return ""
        return " ".join(str(row[0]).split())


__all__ = [
    "RotationDDComponentIdentityGapReport",
    "RotationDDComponentIdentityGapRow",
    "RotationDDComponentIdentityGapService",
]
