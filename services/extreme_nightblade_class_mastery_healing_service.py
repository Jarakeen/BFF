from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from engine.config import get_data_dir
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import canonical_class_skill_line_id


@dataclass(frozen=True)
class ExtremeNightbladeClassMasteryHealingResult:
    selected_masteries: tuple[str, ...]
    critical_healing_bonus: float
    critical_healing_cap: float
    weapon_spell_damage_bonus: float
    unresolved: tuple[str, ...]


class ExtremeNightbladeClassMasteryHealingService:
    """Resolve reviewed U50 Nightblade Class Mastery healing contributions.

    Class Mastery is available only to a pure class with all three native class
    skill lines mastered. Build snapshots persist the two chosen passives as
    ``ClassMasteryAbilityIds``; subclass materialization clears those selections.

    Reviewed U50 healing-relevant Nightblade choices are:

    * ``Above and Beyond``: +25% Critical Healing in PvE (+5% against Battle
      Spirit targets) and raises the total Critical Damage/Healing cap from 125%
      to 155%.
    * ``An Eye for Exploitation``: up to +2000 Weapon and Spell Damage based on
      the heal target's missing Health; the value is halved against Battle Spirit
      targets. The proportional missing-health relation is modeled linearly.

    This resolver reports contributions separately. It does not mutate canonical
    stat state or apply the Critical Healing cap by itself.
    """

    NIGHTBLADE_NATIVE_LINES = frozenset({"assassination", "shadow", "siphoning"})
    MAX_SELECTED_MASTERIES = 2
    BASE_CRITICAL_HEALING_CAP = 1.25
    ABOVE_AND_BEYOND_CAP_INCREASE = 0.30
    ABOVE_AND_BEYOND_PVE_BONUS = 0.25
    ABOVE_AND_BEYOND_BATTLE_SPIRIT_BONUS = 0.05
    EYE_FOR_EXPLOITATION_MAX_POWER = 2000.0

    REVIEWED = frozenset({"above and beyond", "an eye for exploitation"})

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path or get_data_dir() / "eso.db")
        self._identity_cache: dict[int, tuple[str, str] | None] = {}

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def _is_pure_nightblade(cls, build: PlayerBuild) -> bool:
        if cls._normalized(build.EsoClass) != "nightblade":
            return False
        explicit = {
            canonical_class_skill_line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if canonical_class_skill_line_id(value)
        }
        return not explicit or explicit == cls.NIGHTBLADE_NATIVE_LINES

    def _ability_identity(self, ability_id: int) -> tuple[str, str] | None:
        if ability_id in self._identity_cache:
            return self._identity_cache[ability_id]
        if not self.database_path.exists():
            self._identity_cache[ability_id] = None
            return None

        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()}
            if not {"ability_id", "name"}.issubset(columns):
                self._identity_cache[ability_id] = None
                return None
            skill_line_expr = "TRIM(COALESCE(skill_line, ''))" if "skill_line" in columns else "''"
            row = db.execute(
                f"SELECT TRIM(COALESCE(name, '')), {skill_line_expr} FROM ability WHERE ability_id = ? LIMIT 1",
                (int(ability_id),),
            ).fetchone()

        identity = None
        if row is not None and str(row[0] or "").strip():
            identity = (str(row[0]).strip(), str(row[1] or "").strip())
        self._identity_cache[ability_id] = identity
        return identity

    def resolve(
        self,
        *,
        build: PlayerBuild,
        target_health_fraction: float | None = None,
        battle_spirit_active: bool = False,
    ) -> ExtremeNightbladeClassMasteryHealingResult:
        raw_ids = tuple(getattr(build, "ClassMasteryAbilityIds", ()) or ())
        selected_ids: list[int] = []
        unresolved: list[str] = []
        seen: set[int] = set()
        for raw in raw_ids:
            if isinstance(raw, bool):
                unresolved.append(f"Invalid Class Mastery ability id: {raw!r}")
                continue
            try:
                value = int(raw)
            except (TypeError, ValueError):
                unresolved.append(f"Invalid Class Mastery ability id: {raw!r}")
                continue
            if value <= 0:
                unresolved.append(f"Invalid Class Mastery ability id: {raw!r}")
                continue
            if value not in seen:
                seen.add(value)
                selected_ids.append(value)

        if not selected_ids:
            return ExtremeNightbladeClassMasteryHealingResult(
                selected_masteries=(),
                critical_healing_bonus=0.0,
                critical_healing_cap=self.BASE_CRITICAL_HEALING_CAP,
                weapon_spell_damage_bonus=0.0,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        if len(selected_ids) > self.MAX_SELECTED_MASTERIES:
            unresolved.append(
                f"Class Mastery permits at most {self.MAX_SELECTED_MASTERIES} selected passives"
            )
        if not self._is_pure_nightblade(build):
            unresolved.append("Nightblade Class Mastery is unavailable while subclassing or on another base class")

        names: list[str] = []
        valid_names: set[str] = set()
        for ability_id in selected_ids:
            identity = self._ability_identity(ability_id)
            if identity is None:
                unresolved.append(f"Class Mastery ability id {ability_id} is unresolved in canonical ability data")
                continue
            name, skill_line = identity
            names.append(name)
            normalized_name = self._normalized(name)
            normalized_line = self._normalized(skill_line)
            if "class mastery" not in normalized_line or "nightblade" not in normalized_line:
                unresolved.append(
                    f"{name}: selected ability is not proven to belong to Nightblade Class Mastery"
                )
                continue
            if normalized_name not in self.REVIEWED:
                unresolved.append(f"Nightblade Class Mastery healing effect is not reviewed: {name}")
                continue
            valid_names.add(normalized_name)

        legal_selection = (
            len(selected_ids) <= self.MAX_SELECTED_MASTERIES
            and self._is_pure_nightblade(build)
        )
        critical_bonus = 0.0
        critical_cap = self.BASE_CRITICAL_HEALING_CAP
        power_bonus = 0.0

        if legal_selection and "above and beyond" in valid_names:
            critical_bonus += (
                self.ABOVE_AND_BEYOND_BATTLE_SPIRIT_BONUS
                if battle_spirit_active
                else self.ABOVE_AND_BEYOND_PVE_BONUS
            )
            critical_cap += self.ABOVE_AND_BEYOND_CAP_INCREASE

        if legal_selection and "an eye for exploitation" in valid_names:
            if target_health_fraction is None:
                unresolved.append(
                    "An Eye for Exploitation requires explicit heal-target Health fraction"
                )
            else:
                value = float(target_health_fraction)
                if not 0.0 <= value <= 1.0:
                    raise ValueError("target_health_fraction must be between 0 and 1")
                power_bonus = self.EYE_FOR_EXPLOITATION_MAX_POWER * (1.0 - value)
                if battle_spirit_active:
                    power_bonus *= 0.5

        return ExtremeNightbladeClassMasteryHealingResult(
            selected_masteries=tuple(names),
            critical_healing_bonus=critical_bonus,
            critical_healing_cap=critical_cap,
            weapon_spell_damage_bonus=power_bonus,
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
