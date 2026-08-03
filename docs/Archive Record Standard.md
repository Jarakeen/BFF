# Archive Record Standard

**Version:** 0.1
**Status:** Draft

---

# Purpose

The Archive exists to preserve one canonical record for every game concept used by the Black Feather Foundry.

The purpose of this standard is to ensure every record follows the same identity, organization, and quality rules regardless of its source.

Raw data may come from APIs, scraped websites, manual entry, or imported files.

Once a record enters the Archive, its origin should no longer matter.

---

# Core Principles

## I. One Concept, One Record

Every Archive Record represents exactly one game concept.

Examples:

✔ Major Courage

✔ Spell Power Cure

✔ Aggressive Horn

✔ Oakensoul Ring

Not:

✘ Spell Power Cure Boots

✘ Spell Power Cure Gloves

✘ Spell Power Cure Necklace

Those are individual items.

The Archive stores the Gear Set.

---

## II. Canonical Representation

If multiple sources describe the same concept, the Archive stores one canonical record.

Duplicate records are never permitted.

Builders are responsible for collapsing duplicate source data into a single Archive Record.

---

## III. Stable Identity

Every Archive Record receives one permanent Archive Number.

Archive Numbers are never reused.

Names may change.

Descriptions may change.

Relationships may change.

Archive Numbers do not.

---

## IV. Human Readable

Archive Records are intended to be read by people first and machines second.

Field names should be descriptive.

Identifiers should remain understandable.

Example:

buff_major_courage

instead of

000001

---

# Universal Fields

Every Archive Record SHALL contain the following fields.

| Field | Required | Description |
|--------|----------|-------------|
| archive_no | No* | Permanent Foundry identifier assigned by the Archivist |
| id | Yes | Canonical string identifier |
| type | Yes | Record type |
| name | Yes | Display name |
| description | No | Human-readable description |
| icon | No | Icon filename or asset reference |
| aliases | Yes | Alternate names used for searching |
| tags | Yes | Search and classification tags |
| status | Yes | active, deprecated, incomplete, draft |

*archive_no is assigned after the Builder stage.

---

# Record Types

The Archive currently recognizes the following primary record types.

Combat

- Buff
- Debuff
- Status Effect

Skills

- Skill
- Skill Line
- Morph

Equipment

- Gear Set
- Mythic
- Arena Weapon
- Monster Set

Build

- Champion Star
- Mundus
- Food
- Drink
- Potion
- Poison

Content

- Trial
- Dungeon
- Arena
- Zone

Encounter

- Boss
- Mechanic

Progression

- Achievement
- Collectable

Additional record types may be added without changing the Archive Standard.

---

# Builder Responsibilities

Builders SHALL:

- Read raw source data.
- Normalize formatting.
- Remove duplicate concepts.
- Produce canonical Archive Records.
- Populate all required fields.

Builders SHALL NOT:

- Assign archive_no.
- Create relationships.
- Resolve references.
- Query other builders.
- Modify unrelated Archive Records.

---

# Archivist Responsibilities

The Archivist SHALL:

- Assign permanent archive_no values.
- Preserve existing archive_no values.
- Maintain the Archive Registry.
- Reject duplicate identities.

The Archivist SHALL NOT:

- Modify record content.
- Infer relationships.
- Perform gameplay analysis.

---

# Cartographer Responsibilities

The Cartographer SHALL:

- Read canonical Archive Records.
- Resolve references between records.
- Build the Relationship Ledger.
- Validate relationship integrity.

The Cartographer SHALL NOT:

- Modify record identities.
- Rewrite record content.

---

# Validation Rules

Every Archive Record must satisfy the following:

✓ id is unique

✓ name is present

✓ type is valid

✓ required fields exist

✓ aliases contain no duplicates

✓ tags contain no duplicates

✓ no duplicate records represent the same concept

Records that fail validation are rejected.

---

# Archive Philosophy

The Archive preserves concepts, not implementation.

The API may describe hundreds of individual items.

The Archive describes the single idea those items represent.

Example:

API

Spell Power Cure Boots

Spell Power Cure Gloves

Spell Power Cure Ring

Archive

Spell Power Cure

One concept.

One record.

---

# The Granny Rule

When two valid solutions exist:

Choose the one that is easier to understand, easier to maintain, and least likely to create duplicate information.

The Archive values clarity over cleverness.

---

# Future Extensions

The Archive Standard is expected to expand with:

- Relationship Ledger
- Validation Reports
- Provenance Tracking
- Version History
- Localization
- Source Attribution

These additions should extend the Archive rather than replace existing standards.