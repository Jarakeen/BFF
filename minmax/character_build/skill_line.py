from dataclasses import dataclass
from enum import Enum


class SkillLineType(str, Enum):
    """What kind of skill line this is, which determines its access rule."""

    CLASS = "class"
    WEAPON = "weapon"
    ARMOR = "armor"
    GUILD = "guild"
    WORLD = "world"
    ALLIANCE_WAR = "alliance_war"
    RACIAL = "racial"


@dataclass(frozen=True)
class SkillLine:
    """
    A stable skill-line identity.

    `id` is the snake_case identity (e.g. "ardent_flame", "dual_wield").
    Nothing about "how many points are slotted in it" or "how strong its
    passives are" lives here - those are numeric variants attached
    elsewhere (see passive_grant.py), never folded into the identity.
    """

    id: str
    name: str
    line_type: SkillLineType

    owning_class: str | None = None
    """For CLASS lines: which CharacterClass.value owns this line."""
