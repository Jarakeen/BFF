# BFF Project State
# MAIN GOAL -- KEEP HERE #
# ** Given a specific ESO trial encounter, a specific group, and their locked character identities, determine the best encounter-specific builds, skills, support assignments, and rotations to maximize the chance of success, with Safe and Score-Pushing strategies. ** #
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

Encounter
   ↓
Mechanics
   ↓
Strategy
   ↓
Group composition
   ↓
Player identity / role
   ↓
Build
   ↓
Skills
   ↓
Support assignments
   ↓
Rotation / execution
   ↓
Expected outcome

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

Lokkestiiz is now our first encounter-analysis case

We've deliberately chosen Lokkestiiz as the first encounter for the ESO Logs strategy/evidence work.

We have:

Our team

Report:

FPy6Tc9BzwQNbfVK

Fights:

6
27
41
High-performing reference team

Report:

NVDXwL1BQryFTxYh

Fights:

6
8
12

The second dataset is specifically being used as a best-of-the-best reference, rather than merely another random successful clear.

That distinction matters. We're trying to learn:

What does an elite execution actually do?

and compare it against:

What does our group actually do?

rather than declaring the elite team's exact build to be universally correct.


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

Raw ESO Logs data has now been acquired

The elite report was successfully queried through the ESO Logs API.

We created:

data/raw/esologs_nvdx_lokkestiiz.json

Containing:

Fight 6   100,559 events
Fight 8    73,841 events
Fight 12  156,160 events

Our earlier report data also exists in:

data/raw/esologs_probe.json
data/raw/esologs_night2.json

The important architectural decision:

Raw ESO Logs JSON is evidence and should remain separate from the normalized MinMax representation.

We discovered that ESO Logs exposes a large amount of entity-level detail, including player equipment/skills and event data, but its representation is not the representation MinMax should adopt.

For example, a single player can appear fragmented across equipment pieces, skills, and other entities.

Therefore:

ESO Logs schema
      ≠
MinMax domain model

The parser should translate ESO Logs into our canonical domain representation, not force MinMax to behave like ESO Logs.

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

We now have a normalization layer

We created normalized Lokkestiiz output under:

data/normalized/lokkestiiz/

Current examples:

FPy6Tc9BzwQNbfVK_fight_6.json
FPy6Tc9BzwQNbfVK_fight_27.json
FPy6Tc9BzwQNbfVK_fight_41.json

The normalized structure currently looks like:

{
    schema_version,
    source,
    fight,
    players,
    events,
    summary
}

One important discovery:

The current normalization of Fight 6 produced:

players: []
events: 131779

This exposed an important problem with the first normalization approach: the raw ESO Logs combatant/entity representation does not automatically give us the player model we actually need.

Do not treat the current normalized player representation as finished.

The event stream itself is valuable and intact.

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

ESO Logs gave us useful information even before strategy analysis

The Lokkestiiz data demonstrated that the raw event stream contains useful fields including:

timestamp
event type
source
target
ability
damage
healing
resources
HP
Max HP
Magicka
Stamina
Ultimate
Champion Points
position
facing
cast tracking

Example events contain positional information:

x
y
facing

This is potentially extremely valuable for encounter analysis because our eventual system needs to understand positioning and movement, not merely DPS.

The raw JSON should therefore remain preserved as the source of truth.

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

Lokkestiiz strategy knowledge has now been explicitly captured

We have also supplied human strategy knowledge that is not necessarily recoverable from logs alone.

This is critical.

MinMax cannot learn the entire strategy merely by looking at event streams.

For Lokkestiiz, we've established among other things:

Positioning

All three Sunspire dragons are effectively fixed in place.

They do not get repositioned by the tanks.

The meaningful positioning variable is:

dragon facing direction

The group generally positions around the dragon's right-side knuckle on Lokkestiiz and Yolnahkriin, while Nahviintaas uses the opposite side.

The dragons' physical posture also means the group does not get conventional flanking bonuses.

Group positioning

For the Lokkestiiz Storm Fury / "ice laser" phase:

players use assigned positions
the group forms a controlled stack/house
DDs stay as close together as practical without overlapping dangerous effects
healers are assigned responsibility for the stack
healers must sustain the group through the mechanic
some groups use a more diamond-shaped arrangement when operating with one healer
Frozen Tomb / Icy Winds

The human strategy information establishes that these mechanics require:

assigned players
rotation
timing
healing responsibility
avoidance of re-entry/debuff violations

The exact implementation should eventually be represented as mechanic requirements, rather than simply text instructions.

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

We have identified a major distinction: Safe vs Score-Pushing

This needs to become an explicit concept in MinMax.

We aren't looking for one universal "best build."

We need:

Lokkestiiz
├── SAFE
│   ├── more survivability
│   ├── more forgiving mechanics
│   ├── lower execution complexity
│   └── reliable clear
│
└── SCORE-PUSHING
    ├── maximum practical damage
    ├── tighter support coordination
    ├── higher execution demands
    ├── optimized uptime
    └── faster phase transitions

This should eventually become part of the optimization objective, not merely a UI toggle.

For Nahviintaas, we've established that our team uses a portal skip strategy to reduce DD exposure to portal mechanics.

This illustrates another important architectural requirement:

The optimizer needs to understand that:

same encounter
+
different strategy
=
different build requirements

A build optimized for a conventional Nahviintaas portal cycle may not be optimal for a portal-skip strategy.

That is exactly the kind of encounter-specific reasoning the project goal requires.

Tanking strategy has to be represented separately from raw boss mechanics

The current knowledge also establishes that strategy cannot simply say:

"Frost Breath occurs."

It needs to eventually represent:

Mechanic:
    Frost Breath

Role:
    Main Tank

Requirement:
    survive channel

Possible responses:
    block
    dodge
    mitigation
    healing support

Strategy preference:
    blocking is more reliable during normal execution

Failure consequence:
    tank death / potential wipe

This is a decision model, not a mechanic encyclopedia.

That distinction should be preserved as we design the encounter layer.

The ESO Logs comparison should be evidence, not the strategy source

This is probably the most important architectural conclusion from the last few days.

We should not do:

Elite log
   ↓
copy everything elite players did
   ↓
MinMax recommendation

Instead:

ESO mechanics knowledge
        +
human strategy knowledge
        +
elite execution evidence
        +
our group's execution evidence
        ↓
Encounter Model
        ↓
Requirements
        ↓
Candidate solutions
        ↓
MinMax recommendation

ESO Logs can tell us:

What happened?

They cannot independently tell us:

What should have happened?

That distinction needs to be written into the architecture.
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

Proposed new architecture

I would add this to the roadmap:

STATIC ESO DATA
    │
    ├── Skills
    ├── Sets
    ├── Passives
    ├── CP
    ├── Gear
    └── Characters
             │
             ▼
       BUILD MODEL
             │
             ▼
       STAT / EFFECT ENGINE
             │
             ▼
       CANDIDATE BUILDS
             │
             │
ENCOUNTER DATA ───────────────┐
    │                         │
    ├── Mechanics             │
    ├── Phases                │
    ├── Requirements          │
    ├── Positioning           │
    ├── Strategy variants     │
    └── Failure consequences  │
                              ▼
                       ENCOUNTER SOLVER
                              ▲
                              │
ESO LOG EVIDENCE ─────────────┘
    │
    ├── observed execution
    ├── timing
    ├── damage
    ├── healing
    ├── buffs/debuffs
    ├── deaths
    ├── positioning
    └── player behavior

That is the architecture I think we should be aiming at.

---

# 10. REGENERATION STATUS

At present, assume both the live combat-log data and gear-customization data are **retain-only** until the missing importers/tooling are located.

Do not assume either dataset can safely be regenerated.

This is especially important for the combat logs because the repository contains no known importer capable of reconstructing the current 1.75 million-event dataset.


New immediate roadmap

I'd update the old roadmap from:

Build-level effect orchestration → stat resolver → optimizer

to this slightly expanded path:

A. Finish current MinMax foundation
Build-level effect orchestration
gear customization
race
skills/passives
CP
mundus/food/potions
deterministic stat resolution
B. Build encounter evidence pipeline
raw ESO Logs preservation
normalized encounter events
canonical player representation
fight comparison
phase timing extraction
mechanic-event identification
C. Build encounter model
mechanics
phases
role requirements
positioning requirements
survival requirements
damage requirements
support requirements
strategy variants
D. Build strategy model
Encounter
├── Safe
└── Score-Pushing

with potentially additional strategy variants later.

E. Connect encounter → build optimization

Then MinMax can finally answer:

"Given these twelve people, these locked classes/roles, this encounter, and this strategy, what should everyone run?"

That is much closer to the actual product.

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

What I would NOT put into the Project State yet

I would not claim that:

the ESO Logs parser is complete
the Lokkestiiz encounter model is complete
the elite-vs-team analysis is complete
the normalized player model is complete
the optimizer can currently make encounter-specific recommendations
the raw logs have already yielded definitive build conclusions

We have evidence and infrastructure, not conclusions yet.

And that distinction will save us from future Claude conversations confidently building an entire cathedral on top of one malformed JSON field. 🫠

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

# 18. CURRENT MIN/MAX ENGINE STATE

**Status: ACTIVE DEVELOPMENT — DATABASE-BACKED GEAR SET CALCULATION IS WORKING**

The Min/Max engine has progressed from an isolated calculation layer to a real database-backed gear-set calculation path.

### Current branch

```text
integrate-uesp-into-wireframe

75bdd00  Integrate gear sets into minmax build model
4c8013f  Add conditional calculation context
7ad5640  Add Phase 1 gear set effect resolution
bcbedb3  Document current minmax and database state

The current local branch is one commit ahead of:
origin/integrate-uesp-into-wireframe

Current Min/Max test status
107 passed

The full configured Min/Max test suite is currently green.

# 19. COMPLETED MIN/MAX MILESTONES

Database-backed EffectResolver

Existing:

services/minmax/effect_resolver.py

The resolver converts supported ESO effect descriptions into Effect objects.

It deliberately does not guess at unsupported mechanics.

Gear-set data access

Existing:

services/minmax/gear_sets.py
services/minmax/gear_set_repository.py

The repository reads:

gear_set
gear_set_bonus

from the real local data/eso.db.

No duplicate gear-set importer was created.

Gear-set effect resolution

Existing:

services/minmax/gear_set_effect_resolver.py

Phase 1 resolution supports static stat bonuses and selected conditional effects.

Unsupported proc/triggered mechanics are intentionally left unresolved rather than guessed.

Conditional calculation context

Existing:

services/minmax/calculation_context.py

Conditional effects can be represented and evaluated through calculation context.

Archer's Mind provides the current conditional-effect test case.

Gear-set effect service

Existing:

services/minmax/gear_set_effect_service.py

The service connects:

GearSetRepository
        ↓
active piece-count bonuses
        ↓
GearSetEffectResolver
        ↓
Effect[]

Only bonuses whose piece count is less than or equal to the equipped piece count are activated.

For example:

5-piece set
    ↓
2-piece bonus  → active
3-piece bonus  → active
4-piece bonus  → active
5-piece bonus  → active

Unsupported 5-piece proc effects are not fabricated into static effects.

Build gear representation

Existing:

services/minmax/build_gear.py

Build now supports equipped gear sets:

BuildGearSet
├── set_id
└── piece_count

Build now contains:

Build
├── name
├── base_stats
├── gear_sets
└── effects

The build model records equipment without making Build responsible for parsing ESO tooltip mechanics.

Database → Build → StatEngine integration

The first complete database-backed calculation path is working:

data/eso.db
    ↓
GearSetRepository
    ↓
GearSetEffectService
    ↓
GearSetEffectResolver
    ↓
Effect[]
    ↓
Build
    ↓
StatEngine
    ↓
CalculationResult

Verified against real database data using Akaviri Dragonguard.

The calculation preserves effect sources so individual stat contributions can be explained.

Example:

Maximum Health
    Base:                10,000
    Akaviri Dragonguard: +1,206
    --------------------------------
    Total:               11,206

# 20. CURRENT MIN/MAX ARCHITECTURE

The current foundation is intentionally layered:

DATABASE
    ↓
GearSetRepository
    ↓
GearSetEffectService
    ↓
GearSetEffectResolver
    ↓
Effect
    ↓
Build
    ↓
StatEngine
    ↓
CalculationResult
    ↓
StatBreakdown

Responsibilities remain separated:

Repository
    = database access


Resolver
    = tooltip/effect interpretation


Service
    = active set-bonus orchestration


Build
    = canonical build state


StatEngine
    = deterministic stat calculation

Do not move database access into StatEngine.

Do not make Build parse ESO descriptions.

Do not duplicate effect parsing logic between gear sets and the general EffectResolver without a demonstrated need.

# NEXT DEVELOPMENT STATE

The next milestone is:

Build-level effect orchestration

Currently a caller can explicitly do:

build.add_gear_set(set_id, piece_count)

but the gear set must still be resolved into effects by an external caller.

The next step is to make the build calculation pipeline automatically resolve:

Build.gear_sets
        ↓
GearSetEffectService
        ↓
Build.effects
        ↓
StatEngine

The goal is for the build itself to become the complete calculation input.

Conceptually:

Build
├── base stats
├── equipped gear sets
└── explicit effects
        ↓
Build Effect Orchestration
        ↓
resolved Effects
        ↓
StatEngine
        ↓
final stats + breakdown

This should be implemented as a small orchestration layer.

Do not put SQLite access directly into StatEngine.

# MIN/MAX ROADMAP

After build-level gear orchestration is working:

Phase 1 — Deterministic character stat resolution

Connect:

Build
    ↓
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
enchantments
    ↓
sets
    ↓
Champion Points
    ↓
mundus
    ↓
food
    ↓
final character stats

The result must remain inspectable.

A final stat should be explainable as a collection of contributions rather than only producing a number.

Phase 2 — Racial effects

Add:

Race
    ↓
racial passives
    ↓
Effects

Racial bonuses are not yet connected to the current Build → StatEngine pipeline.

The StatEngine can consume racial effects once they are represented as Effect objects, but the database/application orchestration for race is not yet implemented.

Phase 3 — Gear customization

Connect the existing live database tables for:

traits
glyphs
enchantments
weapon traits
armor traits
jewelry traits

These should feed the same Effect pipeline rather than creating a separate stat calculation system.

Phase 4 — Skills and passives

Connect skill/passive data into the same effect/modifier system.

Phase 5 — Champion Points

Connect CP allocations and their resulting modifiers.

Phase 6 — Mundus, food, potions and other temporary character configuration

These should also resolve into the same calculation pipeline.

Phase 7 — Complex/proc mechanics

Only after deterministic static stat resolution is trustworthy should the engine expand support for mechanics such as:

Briarheart
Trial by Fire
Night Terror
Knight Slayer
Spectre's Eye
Whitestrake's Retribution
Shared Pain

These require richer conditional, triggered, scaling, or target-aware mechanics and should not be forced through the simple static stat resolver.

Phase 8 — Min/Max optimization

Once stat resolution is trustworthy:

Build constraints
        ↓
candidate builds
        ↓
StatEngine
        ↓
scored results
        ↓
optimal configuration
Phase 9 — Encounter-aware optimization

Use the completed UESP encounter data to introduce practical encounter constraints:

movement
target uptime
mechanic requirements
survivability
sustain
required defenses

The eventual goal is not merely:

highest theoretical DPS

but:

highest practical performance for this encounter
Phase 10 — UI build calculator

Finally connect the deterministic build/stat engine to the application UI.

# 23. CURRENT DEVELOPMENT PRINCIPLES

The Min/Max engine should follow these principles:

Real database data first.
Deterministic calculations.
Effects are the common currency of stat modification.
Unsupported mechanics must be explicit rather than guessed.
Every important final stat should be explainable through its sources.
Repositories access data; resolvers interpret data; services orchestrate; StatEngine calculates.
Do not commit the production database.
Keep each architectural layer independently testable.
Do not broaden the resolver merely because one new tooltip is complicated.
Preserve green checkpoints before moving to the next layer.

# 24. RECOVERY CHECKPOINT

Current safe Min/Max checkpoint:

75bdd00  Integrate gear sets into minmax build model

Current test baseline:

107 passed

Current branch:

integrate-uesp-into-wireframe

Before continuing Min/Max development:

git status
git branch --show-current
git log -5 --oneline --decorate
python -m pytest services/minmax/tests -q

Expected:

integrate-uesp-into-wireframe

and:

107 passed

Do not reset or revert the Min/Max work to the older UESP-only checkpoints.

# 25. NEW CHAT HANDOFF

If this project is continued in another conversation, the important current state is:

UESP encounter pipeline
    = COMPLETE


Gear customization database migration
    = COMPLETE locally


Gear-set repository
    = COMPLETE


Phase 1 gear-set effect resolver
    = COMPLETE


Conditional calculation context
    = COMPLETE


Gear-set effect service
    = COMPLETE


Build equipped-gear representation
    = COMPLETE


Database-backed gear-set calculation
    = COMPLETE


107 Min/Max tests
    = PASSING


NEXT:
Build-level effect orchestration

The immediate goal is now to make:

build.add_gear_set(set_id, piece_count)

part of the normal build-calculation pipeline so that a caller does not have to manually resolve gear-set effects before invoking StatEngine.

Do not reopen completed UESP encounter work unless a new application requirement exposes a real data/parsing defect.


# 26. ESO LOGS / ENCOUNTER ANALYSIS PIPELINE

## Status

ACTIVE DEVELOPMENT — FIRST ENCOUNTER: LOKKESTIIZ

The project has expanded from deterministic character/build calculation toward
the full encounter-aware Min/Max goal.

The long-term goal remains:

Given a specific ESO trial encounter, a specific group, and their locked
character identities, determine the best encounter-specific builds, skills,
support assignments, and rotations to maximize the chance of success, with
Safe and Score-Pushing strategies.

## Lokkestiiz Evidence Dataset

Two ESO Logs reports are currently being used for the first encounter study.

Our team:

Report:
FPy6Tc9BzwQNbfVK

Fights:
6
27
41

High-performing reference team:

Report:
NVDXwL1BQryFTxYh

Fights:
6
8
12

The reference report represents a best-of-the-best comparison dataset.

Raw elite fight data:

data/raw/esologs_nvdx_lokkestiiz.json

Event counts:

Fight 6: 100,559
Fight 8: 73,841
Fight 12: 156,160

Existing raw Lokkestiiz data also includes:

data/raw/esologs_probe.json
data/raw/esologs_night2.json

## ESO Logs Architecture Principle

ESO Logs is an evidence source, not the Min/Max domain model.

Do not reproduce the ESO Logs entity structure inside MinMax.

Raw ESO Logs should remain preserved as source-of-truth evidence.

The normalization layer should translate ESO Logs into the project's canonical
combat/encounter representation.

Conceptually:

ESO Logs
    ↓
Raw evidence
    ↓
Normalization
    ↓
Canonical encounter events
    ↓
Encounter analysis
    ↓
Encounter model

## Normalized Data

Current normalized Lokkestiiz data exists under:

data/normalized/lokkestiiz/

Current files include:

FPy6Tc9BzwQNbfVK_fight_6.json
FPy6Tc9BzwQNbfVK_fight_27.json
FPy6Tc9BzwQNbfVK_fight_41.json

The normalized schema currently contains:

schema_version
source
fight
players
events
summary

The current player normalization is NOT considered complete.

A raw fight can contain extensive event/entity information without directly
mapping to the canonical player model required by MinMax.

Do not force MinMax to match the ESO Logs representation.

## Useful ESO Logs Evidence

Raw events can provide information including:

timestamp
event type
source/target
ability IDs
damage
healing
resources
HP
Magicka
Stamina
Ultimate
Champion Points
position
facing
cast tracking

Position and facing data may eventually support encounter positioning and
movement analysis.

raw_json must remain preserved.

## Lokkestiiz Strategy Knowledge

Human-provided strategy knowledge is being combined with ESO Logs evidence.

Important known strategy concepts include:

- Dragons are effectively stationary.
- Tank positioning primarily controls dragon facing.
- Lokkestiiz and Yolnahkriin generally use the right-side group position.
- Nahviintaas generally uses the opposite side.
- The dragons' physical posture means conventional flanking assumptions should
  not be applied.
- Storm Fury / ice-laser execution uses assigned player positions.
- DDs remain tightly grouped while avoiding dangerous overlaps.
- Healers are assigned stack-healing responsibility.
- One-healer and two-healer execution patterns may differ.
- Frozen Tomb / Icy Winds require deliberate player rotations.
- Nahviintaas can use a portal-skip strategy to reduce portal exposure for DDs.

These are strategy inputs, not claims that the ESO Logs parser can independently
derive the correct strategy.

## Safe vs Score-Pushing

Encounter optimization must support at least two strategy objectives:

SAFE
- prioritize clear reliability
- prioritize survivability
- reduce execution complexity
- favor forgiving assignments

SCORE-PUSHING
- maximize practical damage
- optimize uptime
- exploit controlled encounter windows
- accept greater execution requirements where justified

There is not necessarily one universally optimal build for an encounter.

The same encounter may produce different optimal builds depending on the
selected strategy.

## Evidence Principle

ESO Logs answers:

"What happened?"

The encounter/strategy model must answer:

"What should happen?"

Therefore recommendations must not simply copy elite-log behavior.

The intended evidence pipeline is:

ESO mechanics/reference data
    +
human strategy knowledge
    +
elite execution evidence
    +
our team's execution evidence
    ↓
Encounter Model
    ↓
Requirements
    ↓
Candidate Builds / Assignments
    ↓
Min/Max Recommendation

## New Encounter-Aware Architecture

Static ESO data:
    skills
    sets
    passives
    CP
    gear
    characters

        ↓

Build Model
        ↓
Stat / Effect Engine
        ↓
Candidate Builds

Encounter Model:
    mechanics
    phases
    role requirements
    positioning
    survival requirements
    damage requirements
    support requirements
    strategy variants

        ↓

Encounter Solver

ESO Logs Evidence feeds the Encounter Solver through observed execution data.

## Immediate Encounter Work

The next ESO Logs milestone is NOT another raw-log parser.

Build a comparison/evidence tool that compares:

Our team:
FPy6Tc9BzwQNbfVK fights 6/27/41

Reference team:
NVDXwL1BQryFTxYh fights 6/8/12

The comparison should eventually expose:

- fight duration
- composition
- phase timings
- deaths
- damage
- healing
- major buff/debuff uptime
- ultimate usage
- mechanic execution
- positioning where reliably derivable

Do not interpret differences as build problems automatically.

Separate:

- build effects
- strategy effects
- execution effects
- player-performance effects

before using them as optimization inputs.

## Encounter-Aware Min/Max Roadmap

1. ~~Finish build-level effect orchestration.~~
2. Complete deterministic character stat resolution.
3. Establish canonical ESO Logs event/player normalization.
4. Build encounter evidence/comparison tooling.
5. Define the Lokkestiiz encounter model.
6. Define Safe and Score-Pushing strategy models.
7. Connect encounter requirements to candidate builds.
8. Add support assignment optimization.
9. Add rotation/timeline optimization.
10. Generalize the encounter framework beyond Lokkestiiz.

## Important Constraint

Do not let ESO Logs schema become the application's domain model.

Do not infer strategy solely from elite logs.

Do not hard-code one team's strategy as universally optimal.

The system must preserve the distinction between:

observed behavior
known mechanics
strategy choice
optimization objective
recommended solution