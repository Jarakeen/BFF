from dataclasses import dataclass

from .effect_layer import BarId
from .slotted_skill import SlottedSkill
from .weapon import Weapon
from .weapon_type import WeaponSkillLine, WeaponType, resolve_weapon_skill_line

ACTIVE_SLOT_COUNT = 5
TOTAL_SLOT_COUNT = ACTIVE_SLOT_COUNT + 1
ULTIMATE_SLOT_INDEX = ACTIVE_SLOT_COUNT


@dataclass(frozen=True)
class Bar:
    """
    One weapon bar's complete mechanical state: its own weapon(s), its own
    six slots (five active skills + one ultimate), and therefore its own
    weapon skill-line access. Front and back bar are two independent
    instances of this type - nothing here assumes they match.
    """

    bar_id: BarId
    main_hand: Weapon
    off_hand: Weapon | None
    slots: tuple[SlottedSkill, ...]

    @property
    def weapon_skill_line(self) -> WeaponSkillLine:
        """The weapon skill line this bar's equipped weapon(s) make available."""
        off_hand_type = (
            self.off_hand.weapon_type if self.off_hand is not None else WeaponType.NONE
        )
        return resolve_weapon_skill_line(self.main_hand.weapon_type, off_hand_type)

    @property
    def active_skills(self) -> tuple[SlottedSkill, ...]:
        """The five non-ultimate skill slots."""
        return self.slots[:ACTIVE_SLOT_COUNT]

    @property
    def ultimate(self) -> SlottedSkill | None:
        """The single ultimate slot, if filled."""
        if len(self.slots) <= ULTIMATE_SLOT_INDEX:
            return None
        return self.slots[ULTIMATE_SLOT_INDEX]

    def violations(self) -> tuple[str, ...]:
        """
        Hard-constraint violations local to this bar alone: finite slot
        count and exactly one ultimate, in the ultimate slot.

        Class/passive ownership and weapon/skill-line compatibility need
        the character's class and a skill-line registry, so those are
        checked one level up, in CharacterBuild.validate().
        """
        problems: list[str] = []

        if len(self.slots) != TOTAL_SLOT_COUNT:
            problems.append(
                f"{self.bar_id.value} bar must have exactly {TOTAL_SLOT_COUNT} "
                f"slots ({ACTIVE_SLOT_COUNT} active + 1 ultimate), got "
                f"{len(self.slots)}."
            )
            return tuple(problems)

        ultimate_flags = [slot.is_ultimate for slot in self.slots]
        ultimate_count = sum(ultimate_flags)

        if ultimate_count != 1:
            problems.append(
                f"{self.bar_id.value} bar must have exactly one ultimate slot, "
                f"found {ultimate_count}."
            )
        elif not ultimate_flags[ULTIMATE_SLOT_INDEX]:
            problems.append(
                f"{self.bar_id.value} bar's ultimate must occupy the ultimate "
                f"slot (index {ULTIMATE_SLOT_INDEX})."
            )

        try:
            self.weapon_skill_line
        except ValueError as exc:
            problems.append(str(exc))

        return tuple(problems)
