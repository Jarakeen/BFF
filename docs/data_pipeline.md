# Data Pipeline

**Version:** 1.0 Draft

---

# Purpose

The Data Pipeline defines how information moves from external sources into the Archive and ultimately becomes available to the Composition Engine.

Every dataset follows the same processing stages.

---

# Pipeline Overview

```
External Sources
        │
        ▼
Raw Data
        │
        ▼
Builders
        │
        ▼
Archive Records
        │
        ▼
Archive Registry
        │
        ▼
Relationship Builder
        │
        ▼
Validation
        │
        ▼
Composition Engine
```

Each stage has one clearly defined responsibility.

---

# Stage 1 — External Sources

The Archive may import data from multiple sources.

Examples

- ESO API
- UESP
- Manual Entry
- Text Imports
- Future Data Sources

Source data should never be modified directly.

---

# Stage 2 — Raw Data

Raw Data is an unmodified copy of imported information.

Examples

```
buff.txt

gear_sets_raw.json

skills_raw.json
```

Purpose

- Preserve original data
- Allow rebuilding
- Support source verification

---

# Stage 3 — Builders

Builders convert Raw Data into Archive Records.

Examples

```
BuffBuilder

DebuffBuilder

GearSetBuilder

SkillBuilder
```

Responsibilities

- Parse source data
- Normalize formatting
- Merge duplicate concepts
- Produce Archive Records

Builders never assign archive_no values.

Builders never create relationships.

---

# Stage 4 — Archive Records

Builders produce canonical datasets.

Examples

```
buffs.json

gear_sets.json

skills.json
```

Each record follows the Archive Record Standard.

---

# Stage 5 — Archive Registry

The Archive Registry assigns permanent archive_no values.

Responsibilities

- Assign new archive_no values
- Preserve existing archive_no values
- Prevent duplicate identities

The Archive Registry never changes gameplay data.

---

# Stage 6 — Relationship Builder

The Relationship Builder creates connections between Archive Records.

Examples

```
Spell Power Cure

grants

Major Courage
```

Relationships are stored separately from Archive Records.

---

# Stage 7 — Validation

Validation checks the integrity of the Archive.

Examples

- Duplicate IDs
- Missing required fields
- Invalid relationship targets
- Duplicate concepts
- Empty records

Validation reports should be generated before publication.

---

# Stage 8 — Composition Engine

The Composition Engine reads Archive data.

It may

- Analyze builds
- Generate recommendations
- Traverse relationships
- Produce reports

It never modifies Archive Records.

---

# Rebuilding the Archive

Because Raw Data is preserved, the Archive can be rebuilt at any time.

```
Raw Data
    ↓
Builders
    ↓
Archive Records
    ↓
Archive Registry
    ↓
Relationship Builder
    ↓
Validation
```

No manual editing of Archive Records should be required during a normal rebuild.

---

# Design Goals

The Data Pipeline is designed to be

- Repeatable
- Deterministic
- Modular
- Extensible
- Auditable

Every stage should perform one responsibility and produce predictable output.

---

# Future Pipeline Stages

Additional stages may be added as the project evolves.

Possible future stages include

- Localization
- Version Tracking
- Relationship Validation
- Data Quality Reports
- Search Index Generation

These stages should extend the pipeline without changing existing responsibilities.