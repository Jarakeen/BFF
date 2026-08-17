# BFF Project State

> **Purpose:** Persistent handoff for continuing BFF development across ChatGPT/Claude conversations.
> **Last updated:** 2026-08-17

---

## 1. Current Project

**Project:** Black Feather Foundry (BFF) / FoundryDock

BFF is an ESO-focused streaming/analysis application. Current development includes ESO reference data, gear customization, encounter/trial data, and combat-log analysis.

Repository:

```text
Jarakeen/BFF
```

Working project:

```text
BFF/40_Stream Studio/OBS/Scripts/FoundryDock/
```

---

# 2. DATABASE STATE

## Production database

```text
data/eso.db
```

Current measured size:

```text
1,139,970,048 bytes
~1.06 GiB
```

SQLite:

```text
page_size: 4096
page_count: 278,313
free_pages: 0
```

The database genuinely stores approximately 1.06 GiB of data. This is not primarily SQLite free-space bloat.

### GitHub rule

**DO NOT commit the current production database to GitHub.**

The repository contains an older, force-added `data/eso.db` snapshot of approximately 37 MB. The current working production database is much larger and is not the same snapshot.

The repository's `.gitignore` already ignores the `data/` directory.

---

# 3. GEAR CUSTOMIZATION DATA

The following tables were successfully imported into the current production database.

| Table | Rows |
|---|---:|
| `gear_trait_material` | 18 |
| `armor_glyph` | 5 |
| `armor_glyph_effect` | 7 |
| `jewelry_trait` | 11 |
| `jewelry_trait_effect` | 850 |
| `jewelry_glyph` | 20 |
| `jewelry_glyph_effect` | 23 |
| `weapon_enchantment` | 14 |
| `weapon_enchantment_effect` | 20 |
| `weapon_trait_effect` | 10 |

### Indexes created

```text
idx_gear_trait_material_trait
idx_gear_trait_material_type
idx_armor_glyph_effect_glyph
idx_armor_glyph_effect_type
idx_jewelry_trait_effect_lookup
idx_jewelry_trait_effect_trait
idx_jewelry_glyph_effect_glyph
idx_jewelry_glyph_effect_type
idx_weapon_enchantment_effect_enchantment
idx_weapon_enchantment_effect_type
idx_weapon_trait_effect_trait
idx_weapon_trait_effect_type
```

### Validation completed

```text
Orphan jewelry trait effects: 0
Orphan jewelry glyph effects: 0
Orphan weapon enchantment effects: 0
Orphan weapon trait effects: 0

Duplicate jewelry traits: 0
Duplicate jewelry glyphs: 0
Duplicate weapon enchantments: 0
Duplicate weapon trait effects: 0
Duplicate jewelry glyph effects: 0
```

The production migration ultimately completed successfully with all expected row counts.

### Important architecture note

The GitHub repository currently contains no importer/service/parser references to these ten gear-customization tables. They were added to the live production database by tooling outside the tracked repository.

Do not assume the current repository can regenerate these tables.

---

# 4. ESO LOG DATA

The large database size is primarily explained by combat-log data.

Current production database contains:

```text
log_report                         2 rows
log_fight                         16 rows
log_actor                        192 rows
log_event                   1,750,281 rows
log_aura                           0 rows
log_observed_damage_window        52 rows
log_observed_target               16 rows
log_import_manifest                6 rows
```

The `log_event` table contains **1,750,281 events**.

These events represent detailed play-by-play ESO Logs data from an actual trial team running **Sunspire over two nights**.

This is intentional test/analysis data, not accidental database garbage.

---

# 5. LOG_EVENT STRUCTURE

`log_event` contains:

```text
report_code
fight_id
event_index
timestamp
event_type
source_id
source_is_friendly
target_id
target_instance
target_is_friendly
ability_game_id
extra_ability_game_id
amount
hit_type
tick
cast_track_id
resource_change
resource_change_type
other_resource_change
max_resource_amount
waste
overheal
absorbed
stack
raw_json
```

Indexes:

```text
idx_log_event_ability
idx_log_event_target
idx_log_event_source
idx_log_event_fight_time
```

plus the primary-key autoindex.

## raw_json

`log_event.raw_json` preserves the original combat event JSON.

A sample event includes source/target resources, HP, Magicka, Stamina, Ultimate, Champion Points, positions, facing, ability IDs, timestamps, and other event metadata.

**DO NOT delete or strip `raw_json` yet.**

It may be important as a source-of-truth / forensic representation if the parser later needs fields that were not initially modeled.

---

# 6. LOG DATABASE ARCHITECTURE

Current working hypothesis:

> Combat-log data probably belongs in a separate `data/eso_logs.db` eventually, while `data/eso.db` remains the stable ESO reference/application database.

Conceptual split:

```text
eso.db
├── ESO reference/static data
├── abilities
├── skills
├── gear sets
├── traits
├── glyphs
├── enchantments
├── encounters
├── achievements
├── roster/team data
└── gear customization

eso_logs.db
├── log_report
├── log_fight
├── log_actor
├── log_event
├── log_aura
├── observed targets
├── observed damage windows
└── raw combat JSON
```

### DO NOT perform this split yet.

The current GitHub repository contains no in-repo code that reads or writes the `log_*` tables.

We do not yet know what external/local tooling created or consumes the combat-log data.

Before moving anything:

1. Identify provenance of the `log_*` tables.
2. Find the external/local importer or script that created them.
3. Determine whether that tooling assumes everything lives in `data/eso.db`.
4. Identify relevant local/untracked/ignored files.
5. Only then design the database split.

---

# 7. CLAUDE REPOSITORY ASSESSMENT

A read-only repository assessment found:

- No in-repo log-import architecture.
- No code reading/writing `log_event`, `log_report`, `log_fight`, `log_actor`, `log_aura`, etc.
- No in-repo combat-log `raw_json` handling.
- No in-repo references to the ten new gear-customization tables.
- No migration system.
- No SQL migration files.
- Schema is created imperatively in Python, particularly through `services/eso_db/schema.py`.
- No use of SQLite `ATTACH DATABASE`.
- Database paths are independently derived at approximately 11 call sites.
- `EsoDatabase`, `EsoAchievementDatabaseService`, and `EsoDbImporter` accept a database path, which is a useful existing pattern.
- `services/roster_service.py` deliberately reuses the existing `EsoDatabase` connection instead of opening a second connection to the same SQLite file.
- `.gitignore` already ignores `data/`.
- `data/eso.db` is nevertheless tracked in Git because it was force-added in an older commit.
- No Git LFS configuration exists.

### Important interpretation

The repository's code and live database are currently out of sync:

```text
GitHub code/schema
        ≠
Current working production database
```

The live database contains data the repository does not currently know how to regenerate.

Treat this as a **data provenance problem**, not merely a database-size problem.

---

# 8. NEXT TASK: DATABASE PROVENANCE FORENSICS

Before any database architecture changes, investigate where the live-only data came from.

Search the entire repository and accessible local project context for:

```text
log_event
log_report
log_fight
log_actor
log_aura
log_observed_target
log_observed_damage_window
raw_json
ESO Logs
esologs
report code
combat log
combat-log
WCL
Warcraft Logs
ATTACH DATABASE
Sunspire
```

Also investigate provenance of:

```text
gear_trait_material
armor_glyph
armor_glyph_effect
jewelry_trait
jewelry_trait_effect
jewelry_glyph
jewelry_glyph_effect
weapon_enchantment
weapon_enchantment_effect
weapon_trait_effect
```

Look in:

- Python
- PowerShell
- JSON
- Markdown
- notebooks
- `dev/`
- `tools/`
- `importers/`
- `parsers/`
- `services/`
- scripts outside the main package
- Git history
- ignored/untracked files where accessible

## Do not modify files or databases during provenance investigation.

The immediate goal is to identify the missing machinery that created the live database content.

---

# 9. DATABASE PATH ARCHITECTURE

The repository currently has no central database-path configuration.

Different code paths independently construct paths such as:

```text
data/eso.db
project_root / data / eso.db
data_dir / eso.db
module-level DB_PATH / DEFAULT_DB_PATH
```

A future cleanup should introduce a central path-resolution layer, for example:

```text
ESO_DB_PATH
ESO_LOGS_DB_PATH
```

But this should be a separate, deliberate change.

Do not combine path-resolution cleanup with an emergency database split.

---

# 10. REGENERATION STATUS

At present, assume both the live combat-log data and gear-customization data are **retain-only** until the missing importers/tooling are located.

Do not assume either dataset can safely be regenerated.

This is especially important for the combat logs because the repository contains no known importer capable of reconstructing the current 1.75 million-event dataset.

---

# 11. GITHUB POLICY

## Do not commit

```text
data/eso.db
data/eso_logs.db
```

Do not commit the current 1.06 GiB database.

The existing 37 MB `data/eso.db` snapshot in Git is an older exception and should not become the pattern.

## Do commit

- Python source
- parsers
- importers
- services
- schema definitions
- migrations, once a migration system exists
- reproducible data-processing code
- small test fixtures when appropriate

## Future test fixtures

A small representative combat-log fixture may eventually be useful for automated tests.

It could contain:

- a small successful pull
- a failed pull
- representative players
- damage events
- healing
- buffs/debuffs
- mechanics
- resource events

Do not commit the full two-night Sunspire event stream merely to provide test data.

---

# 12. CURRENT DO-NOT-DO LIST

Until provenance is understood:

- Do NOT move `log_*` tables.
- Do NOT create `eso_logs.db` as a production replacement.
- Do NOT delete combat logs.
- Do NOT truncate `log_event`.
- Do NOT remove `raw_json`.
- Do NOT strip combat-log indexes just to reduce size.
- Do NOT upload the 1.06 GiB database to GitHub.
- Do NOT assume the current repository can regenerate the live-only data.
- Do NOT modify production schema casually.
- Do NOT combine unrelated architecture cleanups into the log-data investigation.

---

# 13. BACKUP

A production backup was created before the gear-customization migration:

```text
data/eso.db.pre_gear_customization
```

Use backups before future database mutations.

---

# 14. RECENT MIGRATION TOOLING

A migration script was created during the gear-customization migration:

```text
tools/migrate_gear_customization.py
```

It was corrected so it:

- creates only the intended ten tables
- copies validated data
- creates only indexes belonging to those tables
- validates row counts
- commits after successful validation

It should not be treated as a general migration framework.

---

# 15. PROJECT PRINCIPLE

The repository should eventually become the **reproducible source of truth for application/schema/code**, while large runtime/imported datasets remain external/local unless there is a deliberate reason to package a small fixture.

Conceptually:

```text
GitHub
  = code + schema + importers + reproducible logic + tests

Local data
  = production/reference DB + imported combat logs + runtime data
```

The immediate goal is not to make the database smaller.

The immediate goal is to make the relationship between **code, schema, imported data, and external tooling explicit and reproducible**.
