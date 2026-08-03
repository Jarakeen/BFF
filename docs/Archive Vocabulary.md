# Archive Vocabulary

This document defines the terminology used throughout the Archive.

These definitions should remain consistent across documentation, code, and data.

---

## Archive

The complete collection of canonical game data.

---

## Archive Record

One canonical representation of a single game concept.

Every Archive Record follows the Archive Record Standard.

---

## archive_no

A permanent numeric identifier assigned by the Archive Registry.

Archive Numbers are unique and never reused.

---

## Archive Registry

The system responsible for assigning and preserving archive_no values.

---

## Builder

A component that converts raw source data into Archive Records.

Builders never assign archive_no values.

Builders never create relationships.

---

## Canonical

The single accepted representation of a concept.

If multiple sources describe the same concept, one canonical record is created.

---

## Entity

A game concept that deserves its own Archive Record.

Examples

- Buff
- Skill
- Gear Set
- Boss
- Dungeon

---

## Attribute

A fact describing an Entity.

Examples

- Cost
- Duration
- Resource
- Armor Weight

Attributes do not receive archive_no values.

---

## Relationship

A typed connection between two Archive Records.

Examples

- grants
- uses
- belongs_to
- drops
- requires

---

## Relationship Builder

The component responsible for creating relationships between Archive Records.

---

## Validation

The process of checking Archive data for completeness, consistency, and correctness.

---

## Composition Engine

The system that consumes Archive data to analyze builds and answer gameplay questions.

The Composition Engine never modifies Archive data.

---

## Raw Data

Data imported directly from external sources before normalization.

---

## Source

The origin of imported data.

Examples

- ESO API
- UESP
- Manual Entry
- Text Import

---

## Dataset

A collection of related Archive Records.

Examples

- Buffs
- Gear Sets
- Skills
- Mechanics

---

## Entity Type

The classification assigned to an Archive Record.

Examples

- buff
- gear_set
- skill
- boss
- mechanic

---

## Validation Report

A report generated after building data that identifies missing fields, duplicates, or other issues requiring review.