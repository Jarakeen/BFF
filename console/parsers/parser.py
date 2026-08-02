import json
import urllib.request
import re
from pathlib import Path
from typing import List, Dict, Any



# =============================================================================
# Generic API
# =============================================================================







# =============================================================================
# UESP Fetchers
# =============================================================================






#------------
# skill   
#-----------

def _fetch_skill_tree(self) -> list[dict]:
    """Fetch the ESO skill tree definitions."""

    return self._fetch_json(
        table="skillTree",
    )

def _fetch_skill_tree(self) -> list[dict]:
    """Fetch the ESO skill tree definitions."""

    return self._fetch_json(
        table="skillTree",
    )





# =============================================================================
# Record Builders
# =============================================================================




#--------------
#  Skills
#--------------
        
def _build_skill(self, entry: dict) -> dict:

    return {
        "id": entry["id"],
        "name": entry["name"],
        "description": entry["description"],
        "icon": entry["icon"],
        "cast_time": entry.get("castTime"),
        "cost": entry.get("cost"),
        "range": entry.get("range"),
    }



#--------------
#  food
#--------------

def _build_food(self, entry: dict) -> dict:

    description = entry.get("description", "")

    return {
        "id": f"food_{self._slug(entry['name'])}",
        "name": entry["name"],
        "source_layer": "foods",

        "stats_provided": {
            "max_health":
                self._extract_numeric_stat(description, "Max Health"),

            "max_magicka":
                self._extract_numeric_stat(description, "Max Magicka"),

            "max_stamina":
                self._extract_numeric_stat(description, "Max Stamina"),

            "magicka_recovery":
                self._extract_numeric_stat(description, "Magicka Recovery"),

            "stamina_recovery":
                self._extract_numeric_stat(description, "Stamina Recovery"),
        },
    }

#---------------
#  potion
#---------------


def _build_potion(self, entry: dict) -> dict:

    description = entry.get("description", "")

    return {
        "id": f"potion_{self._slug(entry['name'])}",
        "name": entry["name"],

        "source_layer": "potions",

        "base_cooldown_seconds": 45,

        "base_effect_duration_seconds": 36,

        "instant_restoration": {
            "health":
                self._extract_numeric_stat(description, "Health"),

            "magicka":
                self._extract_numeric_stat(description, "Magicka"),

            "stamina":
                self._extract_numeric_stat(description, "Stamina"),
        },
    }



# =============================================================================
# Public Mining Operations
# =============================================================================


# --------------
# Consumables
# --------------

def mine_consumables(self) -> str:
    """Mine food, drink, and potion reference data."""

    try:

        compiled_foods = []
        compiled_potions = []

        # --------------------------------------------------
        # Foods (Type 4)
        # --------------------------------------------------

        for entry in self._fetch_items(4):
            compiled_foods.append(self._build_food(entry))

        # --------------------------------------------------
        # Drinks (Type 12)
        # --------------------------------------------------

        for entry in self._fetch_items(12):
            compiled_foods.append(self._build_food(entry))

        # --------------------------------------------------
        # Potions (Type 7)
        # --------------------------------------------------

        for entry in self._fetch_items(7):
            compiled_potions.append(self._build_potion(entry))

        self._write_to_database("foods.json", compiled_foods)
        self._write_to_database("potions.json", compiled_potions)

        return (
            f"Successfully mined "
            f"{len(compiled_foods)} foods/drinks and "
            f"{len(compiled_potions)} potions."
        )

    except Exception as e:
        return f"Consumable mining failed: {e}"


# --------------
# Skills
# --------------

def mine_skills(self) -> str:
    """Build the skills reference database."""

    try:

        compiled = []

        for entry in self._fetch_mined_skills():
            compiled.append(
                self._build_skill(entry)
            )

        self._write_to_database(
            "skills.json",
            compiled,
        )

        return (
            f"Successfully mined "
            f"{len(compiled)} skills."
        )

    except Exception as e:
        return f"Skill mining failed: {e}"



#--------------
# gear sets
#--------------

def mine_gear_sets(self):

    raw = self._fetch_sets()

    sets = []

    for entry in raw:
        sets.append(
            self._build_set(entry)
        )

    self._write_to_database(
        "gear_sets.json",
        sets,
    )



#-------------
# do the thing
#-------------

def _slug(self, text: str) -> str:
    return (
        text.lower()
            .replace(" ", "_")
            .replace("'", "")
    )



def _fetch_json(self, table: str, **params) -> list[dict]:

    query = "&".join(
        f"{key}={value}"
        for key, value in params.items()
    )

    url = (
        "https://esolog.uesp.net/exportJson.php"
        f"?table={table}"
    )

    if query:
        url += f"&{query}"

    data = self._fetch_raw_web_stream(url)

    return data.get(table, [])