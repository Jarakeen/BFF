# Task: Build Achievement Importer

## Context

This project is FoundryDock, a Python desktop application.

We are building a local archive of ESO data.

The architecture already contains:

- builders/
- parsers/
- models/

There is already a working BossBuilder and BossParser.
Use those as style references.

Do NOT redesign the project.

Do NOT refactor unrelated files.

---

## Data Source

UESP provides a JSON export containing three related tables.

https://esolog.uesp.net/exportJson.php?table[]=achievements&table[]=achievementCriteria&table[]=achievementCategories

The JSON contains:

- achievements
- achievementCriteria
- achievementCategories

Treat these as relational data.

---

## Goal

Create an AchievementBuilder that imports the UESP JSON and produces Foundry archive objects.

The builder should preserve relationships between:

Achievement
↓
AchievementCategory

and

Achievement
↓
AchievementCriteria

Do not flatten the data.

---

## Requirements

Create:

models/

    achievement.py

    achievement_category.py

    achievement_criterion.py

Create:

parsers/

    achievement_parser.py

Create:

builders/

    achievement_builder.py

The parser should:

- parse categories
- parse achievements
- parse criteria

The builder should:

- read the exported JSON
- create dataclass objects
- serialize them into

data/
    processed/
        achievements.json

using the same style as BossBuilder.

---

## Constraints

Do NOT introduce SQLite.

Do NOT build any GUI.

Do NOT modify BossBuilder.

Do NOT modify existing parsers.

Do NOT introduce external dependencies.

Stay consistent with the project's existing coding style.

---

## Deliverables

1. Dataclasses
2. Parser
3. Builder
4. Example usage

The code should compile without placeholders.