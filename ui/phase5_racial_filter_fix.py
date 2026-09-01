from __future__ import annotations

"""Fail-closed racial passive filtering for Phase 5 character progression.

Imported ESO skill rows are not consistent enough to trust ``skill_line`` as
the sole race discriminator. This patch therefore treats a known racial
passive name as authoritative race identity, regardless of how the importer
labels its skill line. Rank/max data remain database-backed; the crosswalk is
used only to decide whether a passive belongs to the selected character race.
"""

from collections import defaultdict

from ui import phase5_build_ui_support as phase5

_INSTALLED = False

_RACE_ALIASES = {
    "altmer": "high elf",
    "bosmer": "wood elf",
    "dunmer": "dark elf",
}

_RACIAL_PASSIVE_RACE = {
    # Altmer / High Elf
    "highborn": "high elf",
    "spell recharge": "high elf",
    "syrabane's boon": "high elf",
    "syrabane’s boon": "high elf",
    "elemental talent": "high elf",
    # Bosmer / Wood Elf
    "acrobat": "wood elf",
    "y'ffre's endurance": "wood elf",
    "y’ffre’s endurance": "wood elf",
    "resist affliction": "wood elf",
    "hunter's eye": "wood elf",
    "hunter’s eye": "wood elf",
    # Dunmer / Dark Elf
    "ashlander": "dark elf",
    "dynamic": "dark elf",
    "resist flame": "dark elf",
    "ruination": "dark elf",
    # Argonian
    "amphibian": "argonian",
    "life mender": "argonian",
    "argonian resistance": "argonian",
    "resourceful": "argonian",
    # Breton
    "opportunist": "breton",
    "gift of magnus": "breton",
    "spell attunement": "breton",
    "magicka mastery": "breton",
    # Imperial
    "diplomat": "imperial",
    "tough": "imperial",
    "imperial mettle": "imperial",
    "red diamond": "imperial",
    # Khajiit
    "cutpurse": "khajiit",
    "robustness": "khajiit",
    "lunar blessings": "khajiit",
    "feline ambush": "khajiit",
    # Nord
    "reveler": "nord",
    "stalwart": "nord",
    "resist frost": "nord",
    "rugged": "nord",
    # Orc
    "craftsman": "orc",
    "brawny": "orc",
    "unflinching rage": "orc",
    "swift warrior": "orc",
    # Redguard
    "wayfarer": "redguard",
    "martial training": "redguard",
    "conditioning": "redguard",
    "adrenaline rush": "redguard",
}


def _normalize_race(value: object) -> str:
    race = phase5._clean(value).casefold()
    return _RACE_ALIASES.get(race, race)


def _generic_racial_line(value: object) -> bool:
    line = phase5._clean(value).casefold().replace("_", " ").replace("-", " ")
    line = " ".join(line.split())
    return line in {"racial", "racial skill", "racial skills"}


def _generic_racial_passive_race(name: object) -> str | None:
    return _RACIAL_PASSIVE_RACE.get(phase5._clean(name).casefold())


def _filtered_passive_rows_by_line(self) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    selected_race = _normalize_race(self.race)

    for skill in self.reference.list_skills():
        if not isinstance(skill, dict):
            continue
        if phase5._int(skill.get("is_player")) != 1 or phase5._int(skill.get("is_passive")) != 1:
            continue

        line = phase5._clean(skill.get("skill_line"))
        name = phase5._clean(skill.get("name"))
        if not line or not name:
            continue

        passive_race = _generic_racial_passive_race(name)
        if passive_race is not None:
            if passive_race != selected_race:
                continue
            display_line = f"{self.race} Skills"
        else:
            owner = phase5._clean(skill.get("class_type"))
            if owner and owner.casefold() != self.eso_class.casefold():
                continue

            line_race = phase5._racial_skill_line_race(line, self._race_skill_lines)
            if line_race is not None:
                if _normalize_race(line_race) != selected_race:
                    continue
                display_line = f"{self.race} Skills"
            elif _generic_racial_line(line):
                # A racial-looking row whose passive is not in the verified
                # crosswalk has no safe owner identity, so fail closed.
                continue
            else:
                display_line = line

        line_key = display_line.casefold()
        key = (line_key, name.casefold())
        if key in seen:
            continue
        seen.add(key)
        grouped[display_line].append(skill)

    for rows in grouped.values():
        rows.sort(key=lambda value: phase5._clean(value.get("name")).casefold())
    return dict(sorted(grouped.items(), key=lambda item: item[0].casefold()))


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    phase5.CharacterProgressionDialog._passive_rows_by_line = _filtered_passive_rows_by_line
    _INSTALLED = True
