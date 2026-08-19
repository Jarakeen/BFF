# BFF Project State

> **Purpose:** Persistent handoff for continuing BFF development across ChatGPT/Claude conversations.
> **Last updated:** 2026-08-19

---

## 1. Current Project

**Project:** Black Feather Foundry (BFF) / FoundryDock

**Repository:** `Jarakeen/BFF`

**Working project:** `BFF/40_Stream Studio/OBS/Scripts/FoundryDock/`

BFF is an ESO-focused streaming/analysis application. Current development includes ESO reference data, gear customization, encounter/trial data, combat-log analysis, and a new Min/Max engine.

**Current branch:** `integrate-uesp-into-wireframe`

**Current GitHub HEAD:** `04abe262dc80079ca7ad5191bdfb5a83bc4e028a`

Latest committed change:

```text
04abe26 Build database-backed minmax effect resolution
```

---

# 2. DATABASE STATE

## Production database

```text
data/eso.db
```

Current working production DB is approximately **1.06 GiB**. It contains reference/application data plus imported encounter data, gear customization data, and combat-log data.

**DO NOT commit the current production database to GitHub.** The repository has an older tracked `data/eso.db` snapshot, but the current working database is a much larger and different snapshot. `data/` is ignored for normal development.

---

# 3. GEAR CUSTOMIZATION DATA: COMPLETE AND VALIDATED

The following tables are now present in the current production database and were successfully migrated from the validated staging DB:

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

Migration was performed with `tools/migrate_gear_customization.py` and completed successfully. It requires `data/eso.db.pre_gear_customization`, refuses to overwrite existing target tables, copies only the ten intended tables and their indexes, validates row counts, and commits only after successful validation.

Backup:

```text
data/eso.db.pre_gear_customization
```

### Important finding: 850 jewelry trait rows are correct

`jewelry_trait_effect` is **not duplicated**. Its rows model level/material/quality-dependent trait values.

Trait totals:

```text
Triune       420
Harmony      265
Protective   140
Infused       15
Bloodthirsty  5
Swift         5
```

Schema:

```text
trait_name
 effect_type
 item_type
 quality
 item_level
 value
 unit
```

Examples:

- `Triune`: 3 effects (`max_health`, `max_magicka`, `max_stamina`) × 140 combinations = 420.
- `Harmony`: one effect with 265 level/material/quality combinations.
- `Protective`: one effect with 140 combinations.
- `Infused`: 3 item types × 5 qualities = 15.
- `Bloodthirsty` and `Swift`: 5 jewelry qualities each.

This level-scaled representation is intentional and useful to the Min/Max engine. Do not replace it with hard-coded constants.

### Validation

```text
armor_glyph OK
jewelry_glyph OK
weapon_enchantment OK
weapon_trait_effect OK
jewelry_trait_effect OK

57 passed
```

The Min/Max test suite currently passes **57 tests**.

---

# 4. MIN/MAX ENGINE: CURRENT STATE

The Min/Max engine lives under:

```text
services/minmax/
```

Current components include:

```text
armor_glyph_repository.py
build.py
calculation.py
candidate_requirements.py
combat_effects.py
effect_kinds.py
effect_mapper.py
effect_resolver.py
effects.py
enchantment_calculation.py
glyph_repository.py
group_effects.py
group_evaluation.py
group_evaluator.py
role.py
roster.py
roster_constraints.py
roster_solver.py
roster_types.py
rule_effects.py
rule_repository.py
stat_ids.py
weapon_enchantment_repository.py
```

### Effect model

`Effect` supports `ADD`, `ADD_PERCENT`, `MULTIPLY`, and `SET`, with `FLAT` or `PERCENT` units, plus stat/kind/source and combat/rule metadata.

### Calculation

`calculation.py` produces `StatBreakdown` objects containing `base`, `additive`, `multiplicative`, and `sources`, with final value:

```text
(base + additive) * multiplicative
```

### EffectResolver

`effect_resolver.py` is committed in `04abe26` and converts direct ESO effect descriptions into structured `Effect` objects. It correctly distinguishes percentage from flat effects. The Brutality/Sorcery percentage parsing bug was caught by tests and fixed.

### EffectRepository

A database-backed `EffectRepository` adapter has been created locally to query `effect JOIN effect_variant` and pass descriptions directly to `EffectResolver`. It has 8 dedicated tests.

**Important checkpoint note:** `effect_repository.py` and its dedicated test file are not yet visible on GitHub at the time of this update. They need to be included in the next local Git checkpoint/push.

---

# 5. CURRENT MIN/MAX ARCHITECTURE

```text
ESO DATABASE
     │
     ├── Effects / Effect Variants
     ├── Gear Sets / Set Bonuses
     ├── Jewelry Traits
     ├── Armor Glyphs
     ├── Jewelry Glyphs
     ├── Weapon Enchantments
     └── Weapon Trait Rules
             │
             ▼
      Effect / Rule repositories
             │
             ▼
        EffectResolver
             │
             ▼
          Effect[]
             │
             ▼
           Build
             │
             ▼
        Calculation
             │
             ▼
       StatBreakdown
```

The individual effect sources are working. The missing layer is the **gear/set orchestration layer**.

---

# 6. NEXT MIN/MAX MILESTONE: SET EFFECT REPOSITORY

Do **not** jump directly into a giant `GearPiece`/optimizer implementation.

Next:

```text
services/minmax/set_repository.py
services/minmax/tests/test_set_repository.py
```

Responsibilities:

1. Look up a set by ID/name.
2. Retrieve `gear_set_bonus` rows.
3. Return piece-count bonuses and descriptions.
4. Resolve bonus descriptions through the existing `EffectResolver`.
5. Return structured `Effect` objects.
6. Return an empty result for an unknown set rather than fabricating data.

Existing set schema:

```text
gear_set
    id
    name
    category
    max_equip_count

gear_set_bonus
    id
    set_id
    piece_count
    description

gear_set_item
    set_id
    item_id

gear_set_piece
    id
    set_id
    equip_type
    armor_type
    weapon_type
```

The set repository should reuse `EffectResolver`; do not duplicate description parsing.

---

# 7. NEXT AFTER SET REPOSITORY

After set effects are tested:

```text
SetEffectRepository
        │
        ▼
   GearContext
        │
        ▼
 GearEffectResolver
        │
        ├── set bonuses
        ├── gear trait
        ├── glyph/enchantment
        └── trait/enchantment rules
        │
        ▼
      Effect[]
        │
        ▼
       Build
        │
        ▼
    Calculation
```

A future `GearContext` should carry runtime information needed to resolve level/quality-sensitive effects, conceptually including:

```text
item_id
slot
item_level
quality
trait
enchantment_id / glyph_id
set_id
```

Do not invent a competing item model until the source of actual item candidates is identified.

The current DB has specialized item tables for glyphs/enchantments and set membership, but **does not have a generic `item` table containing every equipped item's level/quality/trait/etc.** Candidate-item generation is therefore a later layer and should not be conflated with effect calculation.

---

# 8. MIN/MAX ROADMAP

Completed:

```text
✅ Effect model
✅ Stat model
✅ Calculation
✅ EffectMapper
✅ EffectResolver
✅ Database EffectRepository work (local; checkpoint pending)
✅ Armor glyph repository
✅ Jewelry glyph repository
✅ Weapon enchantment repository
✅ Weapon trait/rule repository
✅ Jewelry trait/rule data
✅ Gear customization migration
✅ 57 Min/Max tests passing
```

Next:

```text
👉 SetEffectRepository
👉 Set repository tests
👉 GearContext
👉 GearEffectResolver
👉 Integration test: actual gear → Effects → Build → Calculation
👉 Candidate item source / generation
👉 Build scoring / optimization
👉 Group composition optimization
```

Immediate goal: make **actual gear produce explainable Effects**, not yet optimize builds.

---

# 9. GEAR DATA PROVENANCE

Three raw gear-customization JSON files were recovered from Git history commit `9559a2e` after discovering they had been deleted during a later cleanup:

```text
data/raw/armor_glyph.json
data/raw/jewelry_glyph.json
data/raw/weapon_enchantments.json
```

They were originally UTF-16LE and were normalized to valid UTF-8 JSON for the current import pipeline.

Verified test item IDs:

```text
armor_glyph:
  26580 Glyph of Health
  68343 Glyph of Prismatic Defense

jewelry_glyph:
  26581 Glyph of Health Recovery

weapon_enchantments:
  5365 Glyph of Frost
  26845 Glyph of Crushing
  43573 Glyph of Absorb Health
```

The staging DB contained all ten required gear-customization tables before migration.

Do not fabricate missing data when a historical source can be recovered.

---

# 10. COMBAT LOG DATA

Current production DB also contains detailed ESO Logs data from Sunspire over two nights:

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

`log_event.raw_json` is intentionally preserved.

Eventually combat logs may belong in `data/eso_logs.db`, but **do not perform that split yet**. First identify provenance and external/local tooling that created or consumes the log tables.

---

# 11. DATABASE / REPOSITORY PROVENANCE RULES

The live database and GitHub code are not perfectly synchronized:

```text
GitHub code/schema
        ≠
Current working production database
```

The current live DB contains imported data not necessarily reproducible from the tracked repository alone. Treat missing-data issues as provenance problems first. Do not casually alter production schema or assume a dataset can be regenerated.

---

# 12. GITHUB / GIT CHECKPOINT POLICY

Never commit the current large production DB:

```text
data/eso.db
data/eso_logs.db
```

Commit Python source, repositories, parsers/importers, schema definitions, tests, reproducible migration/data-processing code, and `PROJECT_STATE.md`.

### Current checkpoint situation

GitHub branch HEAD is:

```text
04abe26 Build database-backed minmax effect resolution
```

The next checkpoint should include the newly completed `effect_repository.py` work and its tests, plus this updated `PROJECT_STATE.md`, **without** committing the live database.

Before checkpointing locally:

```powershell
git status --short
git diff --stat
git diff --cached --stat
python -m pytest services/minmax/tests -q
```

Expected current result:

```text
57 passed
```

Suggested focused commit message:

```text
Checkpoint minmax gear effect data layer
```

---

# 13. CURRENT DO-NOT-DO LIST

- Do NOT commit the current production database.
- Do NOT create `eso_logs.db` yet.
- Do NOT delete or strip `log_event.raw_json`.
- Do NOT replace level-scaled jewelry trait data with constants.
- Do NOT duplicate effect parsing logic outside `EffectResolver`.
- Do NOT invent a generic item model until the actual candidate-item source is understood.
- Do NOT build the optimizer before the gear-to-effects pipeline is explainable and tested.
- Do NOT combine unrelated database architecture cleanup with Min/Max work.

---

# 14. PROJECT PRINCIPLE

The repository should become the reproducible source of truth for application/schema/code, while large runtime/imported datasets remain external/local unless deliberately packaged as small fixtures.

```text
GitHub
  = code + schema + importers + reproducible logic + tests

Local data
  = production/reference DB + imported combat logs + runtime data
```

For the Min/Max engine:

```text
Database truth
      ↓
Structured Effects
      ↓
Build
      ↓
Explainable Calculation
      ↓
Candidate generation
      ↓
Optimization
```

**The engine should never optimize a number it cannot explain.**
