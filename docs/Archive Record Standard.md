# Archive Record Standard

**Version:** 1.0 Draft  
**Status:** Active Draft

---

# Purpose

The Archive exists to maintain one canonical record for every game concept used by the Composition Engine.

Its purpose is to transform data from multiple sources into a consistent, searchable knowledge base that can be expanded over time.

The Archive is the single source of truth for all gameplay data.

---

# Core Principles

## 1. One Concept, One Record

Every Archive Record represents exactly one game concept.

Examples

✓ Major Courage

✓ Spell Power Cure

✓ Aggressive Horn

✓ Oakensoul Ring

✓ Cloudrest

✓ Z'Maja

Not

✗ Spell Power Cure Boots

✗ Spell Power Cure Gloves

✗ Spell Power Cure Necklace

Builders are responsible for collapsing multiple source records into one canonical record whenever appropriate.

---

## 2. Canonical Representation

If multiple data sources describe the same concept, the Archive stores one canonical record.

Duplicate records are not permitted.

---

## 3. Stable Identity

Every Archive Record receives one permanent `archive_no`.

Once assigned, an `archive_no` is never reused.

Names may change.

Descriptions may change.

Relationships may change.

The `archive_no` remains permanent.

---

## 4. Human Readable

Archive Records should be understandable by people.

Example

```
buff_major_courage
```

instead of

```
000001
```

---

# Archive Lifecycle

Every record follows the same lifecycle.

```
Raw Data
    ↓
Builder
    ↓
Archive Record
    ↓
Archive Registry
    ↓
archive_no Assigned
    ↓
Relationship Builder
    ↓
Validation
    ↓
Composition Engine
```

Each stage has one responsibility.

---

# Archive Components

## Builder

Builders convert raw source data into Archive Records.

Builders SHALL

- Normalize source data
- Merge duplicate concepts
- Populate required fields

Builders SHALL NOT

- Assign archive_no
- Create relationships
- Modify unrelated records
- Perform gameplay analysis

---

## Archive Registry

The Archive Registry maintains permanent archive numbers.

The Registry SHALL

- Assign new archive_no values
- Preserve existing archive_no values
- Reject duplicate identities

The Registry SHALL NOT

- Modify gameplay data
- Create relationships

---

## Relationship Builder

The Relationship Builder creates connections between Archive Records.

The Relationship Builder SHALL

- Resolve references
- Create relationships
- Validate relationship targets

The Relationship Builder SHALL NOT

- Change archive_no
- Modify record content

---

## Composition Engine

The Composition Engine consumes Archive data.

It may

- Traverse relationships
- Analyze builds
- Generate recommendations
- Produce reports

It SHALL NEVER modify Archive Records.

---

# Archive Record

Every Archive Record SHALL contain the following fields.

| Field | Required | Description |
|--------|----------|-------------|
| archive_no | No* | Permanent Archive Number |
| id | Yes | Canonical identifier |
| type | Yes | Record type |
| name | Yes | Display name |
| description | No | Description |
| icon | No | Asset reference |
| aliases | Yes | Alternate names |
| tags | Yes | Classification tags |
| status | Yes | active, deprecated, draft, incomplete |

\* Assigned by the Archive Registry.

---

# Entity Types

Entities represent game concepts.

Entities receive archive_no values.

## Combat

- Buff
- Debuff
- Status Effect

## Skills

- Skill
- Skill Line
- Morph

## Equipment

- Gear Set
- Mythic
- Arena Weapon
- Monster Set

## Build

- Champion Star
- Mundus
- Food
- Drink
- Potion
- Poison

## Content

- Trial
- Dungeon
- Arena
- Zone

## Encounter

- Boss
- Mechanic
- Encounter Phase

## Progression

- Achievement
- Collectible

Additional entity types may be added without changing this standard.

---

# Attributes

Attributes describe an Archive Record.

Examples

- Cost
- Duration
- Cooldown
- Armor Weight
- Resource
- Description

Attributes do not receive archive_no values.

---

# Relationships

Relationships connect Archive Records.

Relationships are stored separately from Archive Records.

Approved relationship types include

- grants
- granted_by
- applies
- removed_by
- uses
- used_by
- belongs_to
- contains
- contains_boss
- contains_phase
- drops
- drops_from
- requires
- unlocks
- scales_with
- synergizes_with
- conflicts_with

Additional relationship types may be added as needed.

---

# Mechanics

Mechanics are Archive Records.

Mechanics describe objective game behavior.

Examples

- Mind Blast
- Heavy Attack
- Portal
- Shatter

Mechanics are not player strategies.

Example

Mechanic

```
Boss creates a cone attack.
```

Strategy

```
Tank faces the boss away from the group.
```

Strategies belong in guides.

Mechanics belong in the Archive.

---

# Validation

Every Archive Record must satisfy the following.

- archive_no is unique (after assignment)
- id is unique
- type is valid
- name exists
- required fields exist
- aliases contain no duplicates
- tags contain no duplicates
- duplicate concepts have been merged

Validation failures should be reported before publication.

---

# Source Attribution

Builders should preserve source information whenever practical.

Example

    json
        "source": {
        "system": "UESP",
        "reference": "Cloudrest",
        "last_imported": "2026-08-03"
        }


Source attribution improves traceability and maintenance.

---

# Terminology

| Term | Definition |
|------|------------|
| Archive | The complete collection of Archive Records |
| Archive Record | One canonical representation of a game concept |
| archive_no | Permanent numeric identifier assigned by the Archive Registry |
| Entity | A game concept represented by an Archive Record |
| Attribute | A fact describing an Entity |
| Relationship | A typed connection between two Archive Records |
| Builder | Converts raw data into Archive Records |
| Archive Registry | Assigns and preserves archive_no values |
| Relationship Builder | Creates and validates relationships |
| Composition Engine | Consumes Archive data to perform analysis |
| Canonical | The single accepted representation of a concept |

---

# Design Rule

When two equally valid representations exist, choose the one that is:

- Easier to understand
- Easier to maintain
- Less likely to duplicate information

The Archive favors clarity over cleverness.

---

# Philosophy

The Archive stores facts.

The Relationship Builder stores connections.

The Composition Engine makes decisions.

Each component has one responsibility and should not perform another component's job.