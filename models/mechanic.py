# models/mechanic.py
from pathlib import Path
import re

from dataclasses import dataclass, field

@dataclass
class Mechanic:
    name: str
    description: str
    damage: str = ""
    counter: str = ""
    tags: list[str] = field(default_factory=list)