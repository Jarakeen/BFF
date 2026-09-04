from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .alliance_support_passive_input_resolver import AllianceSupportPassiveInputResolver
from .armor_glyph_repository import ArmorGlyphEffectRepository
from .armor_passive_input_resolver import ArmorPassiveInputResolver
from .base_character_state import BaseCharacterCalculator
from .block_item_input_resolver import BlockItemInputResolver
from .build_calculation_context import BuildCalculationContext, CombatEnvironment
from .champion_point_static_repository import ChampionPointStaticRepository
from .character_progression import CharacterProgression
from .combat_state import CombatState, IncomingAttackState
from .combat_state_input_resolver import CombatStateInputResolver
from .core_stat_calculator import CoreStatCalculator
from .gear_set_repository import GearSetRepository
from .gear_stat_inputs import GearCalculationInputs, GearStatInputResolver
from .guild_passive_input_resolver import GuildPassiveInputResolver
from .item_base_stats import BaseItemStatResolver
from .jewelry_glyph_repository import JewelryGlyphEffectRepository
from .jewelry_trait_repository import JewelryTraitRepository
from .mundus_repository import MundusRepository
from .one_hand_shield_passive_input_resolver import OneHandShieldPassiveInputResolver
from .provisioning_static_repository import ProvisioningStaticRepository
from .race_repository import RaceRepository
from .skill_line_repository import SkillLineRepository
from .static_build_inputs import StaticBuildInputResolver
from .undaunted_passive_input_resolver import UndauntedPassiveInputResolver
from .warden_passive_input_resolver import WardenPassiveInputResolver


class BuildCalculationContextFactory:
    """Create one calculation snapshot from a canonical build and character state."""

    _GEAR_SLOT_CACHE_FIELDS = (
        "Set",
        "Set2",
        "Trait",
        "Enchant",
        "Weight",
        "Quality",
        "EnchantTier",
        "Level",
        "WeaponType",
    )

    def __init__(
        self,
        calculator: BaseCharacterCalculator | None = None,
        core_calculator: CoreStatCalculator | None = None,
        race_repository: RaceRepository | None = None,
        gear_set_repository: GearSetRepository | None = None,
        armor_glyph_repository: ArmorGlyphEffectRepository | None = None,
        jewelry_glyph_repository: JewelryGlyphEffectRepository | None = None,
        jewelry_trait_repository: JewelryTraitRepository | None = None,
        base_item_resolver: BaseItemStatResolver | None = None,
        mundus_repository: MundusRepository | None = None,
        champion_point_repository: ChampionPointStaticRepository | None = None,
        provisioning_repository: ProvisioningStaticRepository | None = None,
        skill_line_repository: SkillLineRepository | None = None,
        armor_passive_resolver: ArmorPassiveInputResolver | None = None,
        undaunted_passive_resolver: UndauntedPassiveInputResolver | None = None,
        guild_passive_resolver: GuildPassiveInputResolver | None = None,
        alliance_support_passive_resolver: AllianceSupportPassiveInputResolver | None = None,
        one_hand_shield_passive_resolver: OneHandShieldPassiveInputResolver | None = None,
        block_item_resolver: BlockItemInputResolver | None = None,
        combat_state_resolver: CombatStateInputResolver | None = None,
    ) -> None:
        self.calculator = calculator or BaseCharacterCalculator()
        self.core_calculator = core_calculator or CoreStatCalculator()
        self.race_repository = race_repository
        self.base_item_resolver = base_item_resolver or BaseItemStatResolver()
        self.block_item_resolver = block_item_resolver or BlockItemInputResolver()
        self.armor_passive_resolver = armor_passive_resolver or ArmorPassiveInputResolver()
        self.undaunted_passive_resolver = undaunted_passive_resolver or UndauntedPassiveInputResolver()
        self.one_hand_shield_passive_resolver = one_hand_shield_passive_resolver or OneHandShieldPassiveInputResolver()

        database_path = getattr(gear_set_repository, "database_path", None)
        if gear_set_repository is not None and database_path:
            if armor_glyph_repository is None:
                armor_glyph_repository = ArmorGlyphEffectRepository(database_path)
            if jewelry_glyph_repository is None:
                jewelry_glyph_repository = JewelryGlyphEffectRepository(database_path)
            if jewelry_trait_repository is None:
                jewelry_trait_repository = JewelryTraitRepository(database_path)
            if mundus_repository is None:
                mundus_repository = MundusRepository(database_path)
            if champion_point_repository is None:
                champion_point_repository = ChampionPointStaticRepository(database_path)
            if provisioning_repository is None:
                provisioning_repository = ProvisioningStaticRepository(database_path)
            if skill_line_repository is None:
                skill_line_repository = SkillLineRepository(database_path)

        self.skill_line_repository = skill_line_repository
        self.gear_resolver = (
            GearStatInputResolver(
                gear_set_repository,
                armor_glyph_repository=armor_glyph_repository,
                jewelry_glyph_repository=jewelry_glyph_repository,
                jewelry_trait_repository=jewelry_trait_repository,
            )
            if gear_set_repository is not None
            else None
        )
        self._gear_resolution_cache: dict[tuple[object, ...], GearCalculationInputs] = {}
        self.static_build_resolver = StaticBuildInputResolver(
            mundus_repository,
            champion_point_repository=champion_point_repository,
            provisioning_repository=provisioning_repository,
        )
        self.combat_state_resolver = combat_state_resolver or CombatStateInputResolver(champion_point_repository)
        self.warden_passive_resolver = (
            WardenPassiveInputResolver(skill_line_repository)
            if skill_line_repository is not None
            else None
        )
        self.guild_passive_resolver = guild_passive_resolver or (
            GuildPassiveInputResolver(skill_line_repository)
            if skill_line_repository is not None
            else None
        )
        self.alliance_support_passive_resolver = alliance_support_passive_resolver or (
            AllianceSupportPassiveInputResolver(skill_line_repository)
            if skill_line_repository is not None
            else None
        )

    def build(
        self,
        *,
        character_id: str,
        build_id: str,
        build: PlayerBuild,
        progression: CharacterProgression,
        environment: CombatEnvironment = CombatEnvironment.PVE,
        combat_state: CombatState = CombatState(),
        incoming_attack: IncomingAttackState = IncomingAttackState(),
        target_type: str = "monster",
        target_count: int = 1,
        target_resistance: float | None = None,
        fight_duration: float | None = None,
        active_bar: str = "front",
    ) -> BuildCalculationContext:
        attributes = progression.attributes
        race_stats = self._race_stats(build.Race)
        gear = self._gear_inputs(
            build,
            progression=progression,
            active_bar=active_bar,
            combat_state=combat_state,
            incoming_attack=incoming_attack,
        )

        state = self.calculator.calculate(
            attributes=attributes,
            race_stats=race_stats,
            health=gear.health,
            magicka=gear.magicka,
            stamina=gear.stamina,
            health_recovery=gear.health_recovery,
            magicka_recovery=gear.magicka_recovery,
            stamina_recovery=gear.stamina_recovery,
        )
        core_state = self.core_calculator.calculate(
            character_progression=progression,
            base_character=state,
            race_stats=race_stats,
            inputs=gear.core,
        )
        skills = tuple(skill for skill in (*build.FrontBarSkills, *build.BackBarSkills) if str(skill).strip())
        return BuildCalculationContext(
            character_id=character_id,
            build_id=build_id,
            progression=progression,
            character_state=state,
            core_state=core_state,
            environment=environment,
            combat_state=combat_state,
            incoming_attack=incoming_attack,
            target_type=target_type,
            target_count=target_count,
            target_resistance=target_resistance,
            fight_duration=fight_duration,
            selected_skills=skills,
            active_bar=active_bar.casefold(),
            gear_set_counts=gear.set_counts,
            gear_effects_applied=gear.applied_effect_count,
            unresolved_gear_effects=gear.unresolved,
        )

    def _race_stats(self, race_name: str) -> dict[str, float]:
        if self.race_repository is None or not str(race_name).strip():
            return {}
        return self.race_repository.get_stat_map_by_name(str(race_name).strip())

    def _maxed_passive(
        self,
        progression: CharacterProgression,
        passive_name: str,
        *,
        relevant: bool = True,
    ) -> tuple[bool | None, str | None]:
        """Resolve whether verified max-rank math may be applied.

        ``None`` ownership is returned only for legacy callers that supplied no
        individual passive map at all. Production canonical progression uses an
        explicit mapping and therefore fails closed for unknown/partial ranks.
        """
        if not relevant:
            return False, None
        if progression.passive_ranks is None:
            return None, None

        rank = progression.passive_rank(passive_name)
        if rank is None:
            return False, f"Passive rank is not recorded for character: {passive_name}"
        if rank == 0:
            return False, None
        if self.skill_line_repository is None:
            return False, f"Passive max rank cannot be verified without skill repository: {passive_name}"
        maximum = self.skill_line_repository.passive_max_rank(passive_name)
        if maximum is None:
            return False, f"Passive max rank is not available in canonical data: {passive_name}"
        if rank != maximum:
            return False, f"Partial passive rank is not yet modeled: {passive_name} {rank}/{maximum}"
        return True, None

    @staticmethod
    def _append_progression_unresolved(
        result: GearCalculationInputs,
        messages: list[str],
    ) -> GearCalculationInputs:
        clean = tuple(message for message in messages if message and message not in result.unresolved)
        return replace(result, unresolved=result.unresolved + clean) if clean else result

    @classmethod
    def _gear_slot_cache_key(cls, slot) -> tuple[str, ...]:
        return tuple(
            str(getattr(slot, field_name, "") or "")
            for field_name in cls._GEAR_SLOT_CACHE_FIELDS
        )

    @classmethod
    def _gear_resolution_cache_key(
        cls,
        build: PlayerBuild,
        active_bar: str,
    ) -> tuple[object, ...]:
        normalized_bar = str(active_bar or "front").casefold()
        main, offhand = build.active_weapon_slots(normalized_bar)
        armor = tuple(
            (
                str(slot_name),
                tuple(
                    sorted(
                        (str(key), str(value or ""))
                        for key, value in entry.items()
                    )
                ),
            )
            for slot_name, entry in sorted(build.Armor.items())
        )
        return (
            normalized_bar,
            armor,
            cls._gear_slot_cache_key(main),
            cls._gear_slot_cache_key(offhand),
            cls._gear_slot_cache_key(build.Necklace),
            cls._gear_slot_cache_key(build.Ring1),
            cls._gear_slot_cache_key(build.Ring2),
        )

    def _resolved_gear_inputs(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> GearCalculationInputs:
        if self.gear_resolver is None:
            return GearCalculationInputs()
        cache_key = self._gear_resolution_cache_key(build, active_bar)
        cached = self._gear_resolution_cache.get(cache_key)
        if cached is not None:
            return cached
        resolved = self.gear_resolver.resolve(build, active_bar=active_bar)
        self._gear_resolution_cache[cache_key] = resolved
        return resolved

    def _gear_inputs(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        active_bar: str,
        combat_state: CombatState,
        incoming_attack: IncomingAttackState,
    ) -> GearCalculationInputs:
        gear = self._resolved_gear_inputs(build, active_bar=active_bar)
        gear = self.block_item_resolver.apply(gear, build)
        gear = self.base_item_resolver.apply(gear, build, active_bar=active_bar)
        gear = self.static_build_resolver.apply(
            gear,
            build,
            active_bar=active_bar,
            progression=progression,
        )
        gear = self.combat_state_resolver.apply(gear, build, combat_state=combat_state)

        unresolved: list[str] = []
        is_warden = str(build.EsoClass or "").strip().casefold() == "warden"
        flourish, message = self._maxed_passive(progression, "Flourish", relevant=is_warden)
        if message:
            unresolved.append(message)
        advanced_species, message = self._maxed_passive(progression, "Advanced Species", relevant=is_warden)
        if message:
            unresolved.append(message)
        frozen_armor, message = self._maxed_passive(progression, "Frozen Armor", relevant=is_warden)
        if message:
            unresolved.append(message)
        if self.warden_passive_resolver is not None:
            gear = self.warden_passive_resolver.apply(
                gear,
                build,
                active_bar=active_bar,
                flourish_owned=flourish,
                advanced_species_owned=advanced_species,
                frozen_armor_owned=frozen_armor,
            )

        light_line = progression.owns_skill_line("Light Armor")
        medium_line = progression.owns_skill_line("Medium Armor")
        evocation, message = self._maxed_passive(progression, "Evocation", relevant=light_line)
        if message:
            unresolved.append(message)
        concentration, message = self._maxed_passive(progression, "Concentration", relevant=light_line)
        if message:
            unresolved.append(message)
        spell_warding, message = self._maxed_passive(progression, "Spell Warding", relevant=light_line)
        if message:
            unresolved.append(message)
        prodigy, message = self._maxed_passive(progression, "Prodigy", relevant=light_line)
        if message:
            unresolved.append(message)
        wind_walker, message = self._maxed_passive(progression, "Wind Walker", relevant=medium_line)
        if message:
            unresolved.append(message)
        agility, message = self._maxed_passive(progression, "Agility", relevant=medium_line)
        if message:
            unresolved.append(message)
        dexterity, message = self._maxed_passive(progression, "Dexterity", relevant=medium_line)
        if message:
            unresolved.append(message)

        gear = self.armor_passive_resolver.apply(
            gear,
            build,
            light_armor_passives_owned=light_line if progression.passive_ranks is None else False,
            medium_armor_passives_owned=medium_line if progression.passive_ranks is None else False,
            heavy_armor_passives_owned=progression.owns_skill_line("Heavy Armor") if progression.passive_ranks is None else False,
            evocation_owned=evocation,
            concentration_owned=concentration,
            spell_warding_owned=spell_warding,
            prodigy_owned=prodigy,
            wind_walker_owned=wind_walker,
            agility_owned=agility,
            dexterity_owned=dexterity,
        )

        one_hand_line = progression.owns_skill_line("One Hand and Shield")
        fortress, message = self._maxed_passive(progression, "Fortress", relevant=one_hand_line)
        if message:
            unresolved.append(message)
        sword_and_board, message = self._maxed_passive(progression, "Sword and Board", relevant=one_hand_line)
        if message:
            unresolved.append(message)
        deflect_bolts, message = self._maxed_passive(progression, "Deflect Bolts", relevant=one_hand_line)
        if message:
            unresolved.append(message)
        gear = self.one_hand_shield_passive_resolver.apply(
            gear,
            build,
            active_bar=active_bar,
            passives_owned=one_hand_line if progression.passive_ranks is None else False,
            fortress_owned=fortress,
            sword_and_board_owned=sword_and_board,
            deflect_bolts_owned=deflect_bolts,
            incoming_attack=incoming_attack,
        )

        undaunted_line = progression.owns_skill_line("Undaunted")
        undaunted_mettle, message = self._maxed_passive(progression, "Undaunted Mettle", relevant=undaunted_line)
        if message:
            unresolved.append(message)
        gear = self.undaunted_passive_resolver.apply(
            gear,
            build,
            undaunted_passives_owned=undaunted_line if progression.passive_ranks is None else False,
            undaunted_mettle_owned=undaunted_mettle,
        )

        mages_line = progression.owns_skill_line("Mages Guild")
        fighters_line = progression.owns_skill_line("Fighters Guild")
        magicka_controller, message = self._maxed_passive(progression, "Magicka Controller", relevant=mages_line)
        if message:
            unresolved.append(message)
        slayer, message = self._maxed_passive(progression, "Slayer", relevant=fighters_line)
        if message:
            unresolved.append(message)
        if self.guild_passive_resolver is not None:
            gear = self.guild_passive_resolver.apply(
                gear,
                build,
                active_bar=active_bar,
                mages_guild_passives_owned=mages_line if progression.passive_ranks is None else False,
                fighters_guild_passives_owned=fighters_line if progression.passive_ranks is None else False,
                magicka_controller_owned=magicka_controller,
                slayer_owned=slayer,
            )

        support_line = progression.owns_skill_line("Support")
        magicka_aid, message = self._maxed_passive(progression, "Magicka Aid", relevant=support_line)
        if message:
            unresolved.append(message)
        if self.alliance_support_passive_resolver is not None:
            gear = self.alliance_support_passive_resolver.apply(
                gear,
                build,
                active_bar=active_bar,
                support_passives_owned=support_line if progression.passive_ranks is None else False,
                magicka_aid_owned=magicka_aid,
            )

        return self._append_progression_unresolved(gear, unresolved)
