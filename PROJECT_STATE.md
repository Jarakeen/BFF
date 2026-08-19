# BFF Project State

> **Purpose:** Persistent handoff for continuing BFF development across ChatGPT/Claude conversations.
> **Last updated:** 2026-08-19

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

---

# 16. UESP ENCOUNTER / CONTENT PIPELINE CHECKPOINT

**Status: COMPLETE and integrated into the current wireframe development branch.**

The UESP encounter rebuild and arena importer work was completed and verified.

### Current working branch

```text
integrate-uesp-into-wireframe
```

This branch is now the active development branch. It was created from the newer UI wireframe branch so the latest UI work could be preserved while bringing in the completed UESP/backend work.

### Safety baseline

```text
builds-page-wireframe
```

Current baseline commit:

```text
118eb0f  ignore
```

This branch remains untouched as a rollback/safety point.

### Integration commits

```text
70bc673  Configure pytest test discovery
260f9e9  Add crawled UESP encounter data
696339f  Integrate UESP encounter and database pipeline
118eb0f  builds-page-wireframe baseline
```

### UESP implementation now present

The integrated code includes:

```text
models/uesp_models.py

services/eso_db/
services/uesp/
services/uesp/tests/

tools/check_*
tools/debug_uesp_*
tools/import_to_db.py
tools/import_uesp.py
tools/import_uesp_enriched.py
tools/test_*
```

The enriched UESP parser includes encounter strategies, phase extraction, mechanic classification, boss parsing, content parsing, and arena-specific encounter extraction.

### Verified UESP data

The local database currently contains:

```text
Content: 79
Bosses: 438
```

Arena verification:

```text
Blackrose Prison     4 bosses     16 achievements
Dragonstar Arena    13 bosses      2 achievements
Infinite Archive     0 bosses     73 achievements
Maelstrom Arena     20 bosses      3 achievements
Vateshran Hollows    9 bosses     20 achievements
-----------------------------------------------
TOTAL               46 bosses    114 achievements
```

The database tables used for these relationships include:

```text
content
bosses
content_bosses
achievement
content_achievements
boss_achievements
```

### Crawled UESP dataset committed

The following generated UESP JSON dataset is now tracked:

```text
data/uesp/trials/*.json
data/uesp/arenas/maelstrom_arena.json
data/uesp/bosses/*.json
```

The data checkpoint contains 62 UESP JSON files.

### Tests

Project-level pytest configuration was added:

```text
pytest.ini
```

It restricts test discovery to:

```text
services/uesp/tests
```

This prevents legacy duplicate test modules under `old_pages/` from causing pytest import-file mismatch errors.

Current test result:

```text
36 passed
```

The UESP suite was also independently verified at 36/36 before and after the integration.

### Important UI preservation note

The current integration branch is based on the newer `builds-page-wireframe` state.

No `ui/` or `widgets/` changes were introduced as part of the UESP integration checkpoint.

The intended working assumption going forward is:

```text
integrate-uesp-into-wireframe
    = current UI/wireframe
    + completed UESP encounter pipeline
    + verified UESP data
```

Do not merge this back into `builds-page-wireframe` merely to restore the branch name. The integration branch is now the preferred active development branch, while `builds-page-wireframe` remains the rollback baseline.

---

# 17. CURRENT UNTRACKED LOCAL FILES

After the integration commits, the working tree contains these intentionally untracked files:

```text
YOUR_DB_PATH
archives/FN_0001.md
archives/FN_0002.md
data/eso.db.pre_gear_customization
```

Do not use `git add .` without reviewing these first.

`data/eso.db.pre_gear_customization` is a pre-migration production backup and should remain outside Git.

The current large production `data/eso.db` remains subject to the database policy described earlier and should not be committed.

---

# 18. NEXT DEVELOPMENT STATE

The UESP encounter/data integration is complete.

The next work should return to **UI/application development** on:

```text
integrate-uesp-into-wireframe
```

The immediate goal is to continue the latest wireframe/application iteration while using the now-integrated UESP encounter data as the backend source.

Before making major architectural changes, preserve the current checkpoint:

```text
70bc673
```

If a future change becomes risky, the known-safe rollback points are:

```text
70bc673  current integrated checkpoint
696339f  backend integration without crawled JSON data
260f9e9  crawled UESP data checkpoint
118eb0f  original wireframe baseline
```

---

# 19. RECOVERY INSTRUCTIONS FOR A NEW CHAT

If this project needs to be continued in a new ChatGPT/Claude conversation, establish the repository state first:

```powershell
git status
git branch --show-current
git log -8 --oneline --decorate
```

Expected active branch:

```text
integrate-uesp-into-wireframe
```

Expected recent history:

```text
70bc673 Configure pytest test discovery
260f9e9 Add crawled UESP encounter data
696339f Integrate UESP encounter and database pipeline
118eb0f ignore
```

Run the regression suite before modifying the UESP/backend pipeline:

```powershell
python -m pytest -q
```

Expected:

```text
36 passed
```

Do not assume the live production database can be regenerated from Git. The database provenance warnings in Sections 2, 6, 7, 8, 10, and 11 remain in force.

For UI work, treat the current branch as the source of truth. Do not reset to `builds-page-wireframe` unless intentionally rolling back the UESP integration.

---

# 20. HANDOFF SUMMARY

**BFF / FoundryDock is currently at a stable integration checkpoint.**

The major UESP encounter rebuild is finished. Trials, dungeons, and arenas are represented through the new parser/import pipeline. Arena-specific parsing was added after UESP category discovery showed that `Online:Arenas` was not the usable category structure for the desired records, so the importer uses an explicit canonical arena title set.

The UESP data was imported into the local database and verified:

```text
79 content
438 bosses
46 arena boss relationships
114 arena achievements
```

The crawled JSON data was committed separately from the code integration.

The current branch preserves the latest wireframe UI and adds the completed UESP backend/data layer on top.

The project-level test collection problem caused by duplicate legacy tests in `old_pages/` was resolved with `pytest.ini`, and the full configured suite passes:

```text
36 passed
```

**Next task:** resume UI/application development on `integrate-uesp-into-wireframe`.

Do not reopen the completed UESP importer work unless a new application requirement exposes a real data/parsing defect. The current UESP pipeline should be treated as a completed, checkpointed subsystem.




We’re at the point where the min/max engine itself is no longer the immediate blocker. The ugly UESP plumbing is finished, the database has the encounter data, and the wireframe branch has been brought back together. Humanity may yet survive software development. 😏

Current path to the min/max engine

Based on the checkpoint we just established, I’d put the remaining work in this order:

Finish the data foundation
UESP encounters ✅
Arena encounters ✅
Achievements/content relationships ✅
ESO gear/skill data already present
Min/max calculation infrastructure already started on the wireframe branch
Connect the Min/Max engine to the real database
Stop treating the engine as an isolated calculation layer.
Feed it the actual gear_set, gear_set_bonus, traits, glyphs, enchantments, skills, CP, etc.
Make sure its inputs are normalized and deterministic.

Define the build model

We need one canonical representation of a build, something roughly like:

Build
├── class
├── race
├── role
├── level / CP
├── gear
│   ├── set
│   ├── slot
│   ├── weight
│   ├── trait
│   ├── enchantment
│   └── quality
├── weapons
├── skills
├── passives
├── champion points
├── mundus
├── food
└── potions

This is important because otherwise the min/max engine becomes a very sophisticated calculator operating on vibes.

Build the stat-resolution layer

This is the heart of the engine.

Given a build, it should resolve:

base stats
    ↓
race
    ↓
class/passives
    ↓
gear
    ↓
traits
    ↓
enchants
    ↓
sets
    ↓
CP
    ↓
food/mundus/etc.
    ↓
final character sheet

We want the result to be inspectable, not just:

Magicka: 31,482

It should be possible to determine why it is 31,482.

Add optimization

Once stat resolution is trustworthy, the actual min/max layer can ask:

"Given these constraints, what configuration produces the best result?"

For example:

Goal:
    maximize spell damage


Constraints:
    Warden
    Magicka
    PvE
    2-bar
    no mythic
    trial gear allowed


Result:
    recommended sets
    recommended traits
    recommended enchants
    expected stats
    tradeoffs

Then connect encounter data to optimization

This is where the UESP work we just finished becomes particularly valuable.

Instead of merely:

"What gives me the highest DPS?"

BFF can eventually reason about:

"What gives me the highest practical DPS for this encounter?"

Meaning mechanics, movement, target uptime, required defenses, sustain requirements, etc. can become optimization constraints.

The immediate next milestone

I would not jump straight into "make the optimizer smarter."

The next sensible milestone is:

Min/Max Engine v1: deterministic character stat resolution

We should be able to give it a build and get a complete, reproducible stat breakdown.

Something like:

INPUT
Warden
CP 2600
Khajiit
5-piece Set A
5-piece Set B
Monster Set
Specific traits
Specific enchants
Specific skills/passives
CP allocation


                    ↓


STAT RESOLVER


                    ↓


OUTPUT


Health        18,230
Magicka       31,482
Stamina       17,104
Spell Damage   6,842
Crit Chance      68.4%
Penetration    7,240
Crit Damage       125%
...

And critically:

Spell Damage: 6,842


Base                         1,000
Gear                           +X
Weapon                         +X
Set bonuses                    +X
Major Sorcery                 +20%
Minor Sorcery                 +5%
CP                             +X
--------------------------------
Final                         6,842

That is the foundation I would trust before allowing the optimizer to start making recommendations.

Then the roadmap becomes
DATABASE
   ↓
CANONICAL BUILD MODEL
   ↓
STAT RESOLVER          ← NEXT BIG TARGET
   ↓
EFFECT / MODIFIER ENGINE
   ↓
MIN/MAX OPTIMIZER
   ↓
ENCOUNTER-AWARE OPTIMIZER
   ↓
UI BUILD CALCULATOR
   ↓
"Why this build?" explanations

And because we already have the min/max engine work represented in the wireframe history, I would inspect exactly what acca47f min/max engine already implemented before writing another line. There is a very real possibility that some of the stat-resolution foundation is already there and we only need to wire it into the new database architecture.

So the next coding session should be a focused audit of acca47f and the current database schema, then we lock down the canonical Build → Stat Resolver contract. That avoids rebuilding something we already built two days ago, which is apparently one of Git's favorite human pastimes.


Update PROJECT_STATE.md to reflect the current state of the Min/Max and database work.

IMPORTANT:
- Do not modify application code.
- Do not modify data/eso.db.
- Do not add any *.db files to git.
- Preserve the existing structure and information in PROJECT_STATE.md.
- Add/update the current state rather than replacing the document.

Current Git state:
Branch: integrate-uesp-into-wireframe
HEAD: 04abe26
Origin: origin/integrate-uesp-into-wireframe
Latest commit: "Build database-backed minmax effect resolution"

Current accomplishments:
1. Database-backed EffectResolver exists at services/minmax/effect_resolver.py.
2. EffectResolver tests exist and pass.
3. EffectRepository exists and passes its tests.
4. The recovered gear-customization raw JSON files were restored from git commit 9559a2e:
   - data/raw/armor_glyph.json
   - data/raw/jewelry_glyph.json
   - data/raw/weapon_enchantments.json
5. The gear-customization staging database was populated.
6. The gear-customization migration was successfully run into the local data/eso.db.
7. The following tables were successfully migrated:
   - gear_trait_material: 18 rows
   - armor_glyph: 5 rows
   - armor_glyph_effect: 7 rows
   - jewelry_trait: 11 rows
   - jewelry_trait_effect: 850 rows
   - jewelry_glyph: 20 rows
   - jewelry_glyph_effect: 23 rows
   - weapon_enchantment: 14 rows
   - weapon_enchantment_effect: 20 rows
   - weapon_trait_effect: 10 rows
8. Full services/minmax/tests currently pass:
   57 passed
9. Existing gear-set data is already present in the local data/eso.db:
   - gear_set
   - gear_set_bonus
   - gear_set_item
   - gear_set_piece
10. Existing gear-set importer/parser already exists:
   - importers/gear_set_importer.py
   - parsers/gear_set_parser.py
   Do NOT create another gear-set importer.
11. The current local data/eso.db is intentionally gitignored by .gitignore:
   /data/*.db
   Do not change that policy or commit the database.
12. The current database contains the merged encounter/boss data and the gear/effect data.
13. We inspected two large pre-alchemy databases and found no dedicated collection/pet/mount/appearance schema. The only collection-related column discovered was achievement.collectible_id.
14. Collections are therefore NOT the next Min/Max task.

Next intended engineering task:
Connect the existing gear_set / gear_set_bonus data to the Min/Max engine:
gear_set -> GearSetRepository -> set bonus resolution -> Effect -> Build -> Calculation.

Before implementing that layer, inspect representative real gear_set_bonus.description values and determine how much can reuse the existing EffectResolver. Do not duplicate effect parsing logic unnecessarily.

Also document that the local data/eso.db is the working merged database but is intentionally not committed to Git.