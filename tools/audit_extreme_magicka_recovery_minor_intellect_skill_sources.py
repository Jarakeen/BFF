from __future__ import annotations

"""Inspect canonical self-usable Minor Intellect skill sources for Extreme Magicka Recovery.

This is a diagnostic proof step. It does not score the final objective. The reference
buff catalog names candidate abilities, while SkillEffectRepository owns the canonical
linked/supplemental runtime effects. We print both ability identity and resolved effect
semantics so a later frontier can admit only legal self-provided sources.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.named_combat_buffs import canonical_buff_name, effects_for_buff
from minmax.skill_effect_repository import SkillEffectRepository
from minmax.support_target_type import SupportTargetType


CANDIDATES = (
    "Arcanist's Domain",
    "Enchanted Growth",
    "Refreshing Path",
    "Regenerative Ward",
    "Restoring Aura",
)
TARGET_BUFF = "Minor Intellect"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _ability_rows(database: Path, name: str):
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)")}
        wanted = [
            column
            for column in (
                "ability_id",
                "name",
                "class_type",
                "skill_line",
                "skill_type",
                "base_ability_id",
                "rank",
                "morph",
                "target",
                "duration",
                "is_passive",
                "is_player",
                "is_crafted",
            )
            if column in columns
        ]
        rows = db.execute(
            f"SELECT {', '.join(wanted)} FROM ability WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) ORDER BY rank, ability_id",
            (name,),
        ).fetchall()
    return tuple(dict(row) for row in rows)


def _resolved_minor_intellect(repository: SkillEffectRepository, ability_id: int):
    rows = []
    for effect in repository.resolve(ability_id):
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical != TARGET_BUFF:
            continue
        rows.append(
            {
                "effect_name": effect.name,
                "canonical_buff": canonical,
                "source": effect.source,
                "layer": getattr(effect.layer, "value", str(effect.layer)),
                "target": getattr(effect.target_type, "value", str(effect.target_type)),
                "duration": effect.duration,
                "condition": effect.condition,
                "trigger": effect.trigger,
            }
        )
    return tuple(rows)


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = SkillEffectRepository(database)
    print("EXTREME MAGICKA RECOVERY MINOR INTELLECT SKILL SOURCE AUDIT")
    print(f"database={database}")
    buff_effects = effects_for_buff(TARGET_BUFF)
    print(
        f"target_buff={TARGET_BUFF!r} mapped_effects="
        f"{tuple((effect.stat.value, effect.magnitude, effect.kind) for effect in buff_effects)!r}"
    )
    print()

    self_usable = []
    unresolved = []
    for name in CANDIDATES:
        rows = _ability_rows(database, name)
        print(f"ABILITY {name!r} rows={len(rows)}")
        if not rows:
            unresolved.append(f"canonical ability row missing: {name}")
            continue
        seen_effect = False
        for row in rows:
            print(f"  row={row!r}")
            ability_id = int(row["ability_id"])
            resolved = _resolved_minor_intellect(repository, ability_id)
            if resolved:
                seen_effect = True
            for effect in resolved:
                print(f"    minor_intellect_effect={effect!r}")
                target = str(effect["target"] or "").casefold()
                duration = effect["duration"]
                condition = effect["condition"]
                trigger = effect["trigger"]
                legal_self = (
                    target == SupportTargetType.SELF.value.casefold()
                    and duration is not None
                    and float(duration) > 0.0
                    and condition is None
                    and trigger is None
                )
                if legal_self:
                    self_usable.append((name, ability_id, float(duration)))
        if not seen_effect:
            unresolved.append(f"Minor Intellect effect unresolved for canonical ability: {name}")
        print()

    unique_self = tuple(dict.fromkeys(self_usable))
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    print("SUMMARY")
    print(f"self_usable_sources={unique_self!r}")
    print(f"self_usable_source_count={len(unique_self)}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print("NEXT_STEP=use only proven self-usable Minor Intellect sources in the corrected five-normal-slot bar frontier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
