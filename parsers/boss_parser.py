# parsers/boss_parser.py
from pathlib import Path

from models.boss import Boss

from parsers.metadata_parser import MetadataParser
from parsers.health_parser import HealthParser
from parsers.mechanics_parser import MechanicsParser    
from parsers.dialogue_parser import DialogueParser
from parsers.notes_parser import NotesParser


class BossParser:

    def __init__(self):

        self.metadata = MetadataParser()
        self.health = HealthParser()
        self.mechanics = MechanicsParser()
        self.dialogue = DialogueParser()
        self.notes = NotesParser()

    def parse(self, path: Path) -> Boss:

        text = path.read_text(encoding="utf-8")

        boss = self.metadata.parse(text)

        boss.health = self.health.parse(text)

        boss.mechanics = self.mechanics.parse(text)

        boss.hardmode_mechanics = self.mechanics.parse_hardmode(text)

        boss.dialogue = self.dialogue.parse(text)

        boss.notes = self.notes.parse(text)

        return boss