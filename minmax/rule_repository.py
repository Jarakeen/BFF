import sqlite3
from pathlib import Path

from .effects import EffectUnit
from .rule_effects import RuleEffect


class RuleRepository:
    """Loads rule-effect data from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        # Rule tables are canonical reference data during one repository
        # lifetime. Keep an instance-scoped snapshot so repeated build and
        # optimization evaluations do not reopen SQLite for identical lookups.
        # A newly-created repository still observes later database changes.
        self._weapon_trait_names_cache: tuple[str, ...] | None = None
        self._infused_effect_cache: dict[tuple[str, str], RuleEffect] = {}
        self._weapon_trait_rules_cache: dict[str, tuple[RuleEffect, ...]] = {}
        self._weapon_trait_effect_rules_cache: dict[str, tuple[RuleEffect, ...]] = {}

    def list_weapon_trait_names(self) -> tuple[str, ...]:
        """Return every canonical weapon trait material name."""
        if self._weapon_trait_names_cache is not None:
            return self._weapon_trait_names_cache

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT material_name
                FROM gear_trait_material
                WHERE gear_type = 'Weapon'
                  AND material_name IS NOT NULL
                  AND TRIM(material_name) <> ''
                ORDER BY LOWER(TRIM(material_name))
                """
            ).fetchall()
        self._weapon_trait_names_cache = tuple(str(row[0]) for row in rows)
        return self._weapon_trait_names_cache

    def get_infused_effect(
        self,
        *,
        gear_type: str,
        quality: str,
    ) -> RuleEffect:
        cache_key = (str(gear_type), str(quality))
        cached = self._infused_effect_cache.get(cache_key)
        if cached is not None:
            return cached

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    trait_name,
                    effect_type,
                    value,
                    unit
                FROM jewelry_trait_effect
                WHERE trait_name = 'Infused'
                  AND effect_type = 'enchantment_effect'
                  AND item_type = ?
                  AND quality = ?
                """,
                (gear_type, quality),
            ).fetchone()

        if row is None:
            raise ValueError(
                f"No Infused enchantment effect found for "
                f"gear_type={gear_type!r}, quality={quality!r}"
            )

        trait_name, effect_type, value, unit = row

        effect = RuleEffect(
            rule_type=effect_type,
            value=float(value),
            source=trait_name,
            unit=EffectUnit(unit),
            target_system="enchantment",
            gear_type=gear_type,
            quality=quality,
        )
        self._infused_effect_cache[cache_key] = effect
        return effect

    @staticmethod
    def _weapon_rule_effects(rows, *, lookup_label: str) -> list[RuleEffect]:
        effects: list[RuleEffect] = []
        for material_name, effect_type, value, unit, _description in rows:
            if value is None:
                raise ValueError(
                    f"Weapon trait rule has no value: "
                    f"{lookup_label!r} / {effect_type!r}"
                )
            effects.append(
                RuleEffect(
                    rule_type=effect_type,
                    value=float(value),
                    source=material_name,
                    unit=EffectUnit(unit),
                    target_system="weapon_enchantment",
                )
            )
        return effects

    def get_weapon_trait_rules(
        self,
        trait_name: str,
    ) -> list[RuleEffect]:
        """Return weapon rules for one canonical trait *material* name.

        This legacy lookup is intentionally material-oriented because
        ``weapon_trait_effect.material_name`` stores names such as the trait material,
        not gameplay labels such as ``Charged`` or ``Nirnhoned``.
        """
        cache_key = str(trait_name)
        cached = self._weapon_trait_rules_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    material_name,
                    effect_type,
                    value,
                    unit,
                    description
                FROM weapon_trait_effect
                WHERE material_name = ?
                ORDER BY id
                """,
                (trait_name,),
            ).fetchall()

        effects = self._weapon_rule_effects(rows, lookup_label=cache_key)
        snapshot = tuple(effects)
        self._weapon_trait_rules_cache[cache_key] = snapshot
        return list(snapshot)

    def get_weapon_trait_rules_by_effect_type(
        self,
        effect_type: str,
    ) -> list[RuleEffect]:
        """Return canonical weapon-trait rules selected by semantic effect type.

        Gameplay systems should use this when the mechanic identity is the effect
        itself (for example Charged -> ``status_effect_chance``) rather than assuming
        the ``material_name`` column contains the player-facing trait name.
        """
        cache_key = str(effect_type or "").strip()
        if not cache_key:
            raise ValueError("weapon trait effect type is required")
        cached = self._weapon_trait_effect_rules_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    material_name,
                    effect_type,
                    value,
                    unit,
                    description
                FROM weapon_trait_effect
                WHERE effect_type = ?
                ORDER BY id
                """,
                (cache_key,),
            ).fetchall()

        effects = self._weapon_rule_effects(rows, lookup_label=cache_key)
        snapshot = tuple(effects)
        self._weapon_trait_effect_rules_cache[cache_key] = snapshot
        return list(snapshot)

    def get_weapon_enchantment_rules(
        self,
        trait_name: str,
    ) -> list[RuleEffect]:

        return [
            effect
            for effect in self.get_weapon_trait_rules(trait_name)
            if effect.rule_type == "weapon_enchantment_effect"
        ]
