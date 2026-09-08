from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import HealTemporalScope, SkillEffectKind
from minmax.skill_component_text_evidence import extract_component_text_evidence
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
    extract_delayed_heal_runtime_evidence,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


@dataclass(frozen=True)
class RotationHealerCanonicalDelayedTimingResolution:
    source_name: str
    coefficient_number: int
    skill_rank_id: int | None
    ability_id: int | None
    component_fragment: str
    runtime_evidence: RotationHealerDelayedRuntimeEvidence | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.runtime_evidence is not None and not self.unresolved


class RotationHealerCanonicalDelayedTimingService:
    """Resolve coefficient-local delayed healer timing without guessing offsets."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | object | None = None,
        component_repository: RotationHealerU50SkillComponentRepository | object | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.components = component_repository or RotationHealerU50SkillComponentRepository(
            self.database_path
        )

    def resolve(
        self,
        *,
        source_name: str,
        coefficient_number: int,
    ) -> RotationHealerCanonicalDelayedTimingResolution:
        name = str(source_name or "").strip()
        number = int(coefficient_number)
        unresolved: list[str] = []
        evidence: list[str] = []

        if not name:
            return RotationHealerCanonicalDelayedTimingResolution(
                source_name="",
                coefficient_number=number,
                skill_rank_id=None,
                ability_id=None,
                component_fragment="",
                runtime_evidence=None,
                unresolved=("delayed healing source name is required",),
            )

        resolution = self.coefficients.resolve_name(name)
        if resolution.rank is None:
            messages = resolution.unresolved or (
                f"canonical skill identity unresolved for {name}",
            )
            return RotationHealerCanonicalDelayedTimingResolution(
                source_name=name,
                coefficient_number=number,
                skill_rank_id=None,
                ability_id=None,
                component_fragment="",
                runtime_evidence=None,
                unresolved=tuple(messages),
            )

        rank = resolution.rank
        classification = self.components.get_component(rank.skill_rank_id, number)
        if classification is None:
            unresolved.append(
                f"{rank.name} coefficient {number}: canonical healer component identity unavailable"
            )
        elif classification.effect_kind is not SkillEffectKind.HEAL:
            unresolved.append(
                f"{rank.name} coefficient {number}: component is not canonically classified as healing"
            )
        elif classification.heal_temporal_scope is not HealTemporalScope.DELAYED:
            unresolved.append(
                f"{rank.name} coefficient {number}: component is not canonically classified as delayed healing"
            )

        description = self._coef_description(rank.ability_id)
        component_fragment = ""
        runtime: RotationHealerDelayedRuntimeEvidence | None = None
        if not description:
            unresolved.append(
                f"{rank.name}: canonical coef_description is unavailable for delayed timing"
            )
        else:
            component = extract_component_text_evidence(description, number)
            component_fragment = component.fragment
            evidence.extend(component.evidence)
            if not component_fragment:
                unresolved.append(
                    f"{rank.name} coefficient {number}: coefficient-owned text fragment is unavailable"
                )
            else:
                runtime = extract_delayed_heal_runtime_evidence(
                    source_name=rank.name,
                    coefficient_number=number,
                    component_fragment=component_fragment,
                )
                if runtime is None:
                    unresolved.append(
                        f"{rank.name} coefficient {number}: explicit delayed-heal offset is unresolved"
                    )
                else:
                    evidence.extend(runtime.provenance)

        if unresolved:
            runtime = None
        return RotationHealerCanonicalDelayedTimingResolution(
            source_name=rank.name,
            coefficient_number=number,
            skill_rank_id=rank.skill_rank_id,
            ability_id=rank.ability_id,
            component_fragment=component_fragment,
            runtime_evidence=runtime,
            evidence=tuple(dict.fromkeys(evidence)),
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
