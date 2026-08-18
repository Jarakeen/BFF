from enum import Enum


class Role(str, Enum):
    TANK = "tank"
    HEALER = "healer"
    DD = "dd"