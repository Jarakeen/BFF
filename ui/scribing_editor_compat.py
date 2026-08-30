from __future__ import annotations

"""Compatibility bridge for the searchable BuildEditor and scribing support.

The searchable selector extension replaces ``BuildsPage._editor`` with a
zero-extra-argument factory. Scribing needs the selected build so it can inject
that build's configured scribed skills. Keep that composition explicit here
instead of depending on the signature of whichever extension installed first.
"""

import zlib

from services.skill_choice_service import load_skill_choices
from ui.scribing_support import _recipes_for, _synthetic_skill

_INSTALLED = False


def _synthetic_id(recipe) -> int:
    payload = "\x1f".join(
        str(value or "").strip().casefold()
        for value in (
            recipe.ResultName,
            recipe.Grimoire,
            recipe.Focus,
            recipe.Signature,
            recipe.Affix,
        )
    ).encode("utf-8")
    # Keep synthetic configured skills out of ESO's positive ability-ID space.
    return -(zlib.crc32(payload) + 1)


def _configured_skill(recipe) -> dict:
    skill = _synthetic_skill(recipe)
    synthetic_id = _synthetic_id(recipe)
    skill["id"] = synthetic_id
    skill["ability_id"] = synthetic_id
    skill["base_ability_id"] = synthetic_id
    return skill


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.builds_page import BuildsPage
    from widgets.build_editor import BuildEditor

    def editor_with_scribed_recipes(self, build=None):
        cache = getattr(self, "_build_editor_reference_cache", None)
        if cache is None:
            cache = {
                "race_choices": self.reference.list_race_names(),
                "set_choices": self.reference.list_gear_set_names(),
                "skill_choices": load_skill_choices(self.reference.database.database),
                "cp_choices": [
                    point
                    for point in self.reference.list_champion_points()
                    if isinstance(point, dict) and point.get("name")
                ],
                "food_choices": self.reference.list_food_names(),
                "potion_choices": self.reference.list_potion_names(),
            }
            self._build_editor_reference_cache = cache

        skill_choices = list(cache["skill_choices"])
        existing = {
            str(skill.get("name", "")).strip().casefold()
            for skill in skill_choices
            if isinstance(skill, dict)
        }
        for recipe in _recipes_for(build):
            name = recipe.ResultName.strip()
            if not name or name.casefold() in existing:
                continue
            skill_choices.append(_configured_skill(recipe))
            existing.add(name.casefold())

        editor_kwargs = dict(cache)
        editor_kwargs["skill_choices"] = skill_choices
        return BuildEditor(**editor_kwargs)

    BuildsPage._editor = editor_with_scribed_recipes
    _INSTALLED = True
