# builders/boss_builder.py
import json
from dataclasses import asdict
from pathlib import Path

from models.boss import Boss
from parsers.boss_parser import BossParser



class BossBuilder:
    """
    Imports all raw boss files into bosses.json.
    """

    def __init__(
        self,
        raw_folder: Path,
        output_file: Path,
    ):

        self.raw_folder = raw_folder
        self.output_file = output_file

        self.parser = BossParser()


    def build(self):

        database = self.load_database()

        for file in self.raw_folder.glob("*.txt"):

            print(f"Importing {file.name}...")

            boss = self.parser.parse(file)

            print(f"Adding {boss.archive_no}")

            database["bosses"][boss.archive_no] = asdict(boss)

        print(database)

        self.save_database(database)

    def load_database(self):

        if self.output_file.exists():

            text = self.output_file.read_text(
                encoding="utf-8"
            ).strip()

            if text:
                return json.loads(text)

        return {
            "schema_version": 1,
            "bosses": {}
        }

    def save_database(self, database):

        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.output_file.write_text(
            json.dumps(
                database,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )