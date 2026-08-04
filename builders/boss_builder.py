from dataclasses import asdict
from pathlib import Path
import json

from models.boss import Boss


class BossBuilder:

    def __init__(self, raw_folder: Path, output_file: Path):

        self.raw_folder = raw_folder
        self.output_file = output_file

    def build(self):

        database = self.load_database()

        for file in self.raw_folder.glob("*.txt"):

            boss = self.parse_file(file)

            database["bosses"][boss.archive_no] = asdict(boss)

        self.save_database(database)

def load_database(self):

    if self.output_file.exists():

        return json.loads(
            self.output_file.read_text(
                encoding="utf-8"
            )
        )

    return {

        "schema_version": 1,

        "bosses": {}
    }

def save_database(self, database):

    self.output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    self.output_file.write_text(

        json.dumps(
            database,
            indent=4,
            ensure_ascii=False
        ),

        encoding="utf-8"
    )

def parse_file(self, path: Path) -> Boss:

    text = path.read_text(
        encoding="utf-8"
    )

    boss = Boss(

        archive_no=self.extract_archive_number(text),

        name=self.extract_name(text),

        trial=self.extract_trial(text),

        boss_order=self.extract_order(text),
    )

    boss.mechanics = self.extract_mechanics(text)

    boss.hardmode_mechanics = self.extract_hardmode_mechanics(text)

    boss.dialogue = self.extract_dialogue(text)

    boss.notes = self.extract_notes(text)

    return boss

        