# Relationship Types

**Version:** 1.0 Draft

---

# Purpose

Relationship Types define the approved connections between Archive Records.

Relationships describe how two Archive Records are connected.

All Builders and the Relationship Builder should use the relationship types defined in this document.

---

# Relationship Structure

Every relationship has three parts.

```
Source Record

↓

Relationship Type

↓

Target Record
```

Example

```
Spell Power Cure

grants

Major Courage
```

---

# Combat

## grants

Meaning

The source grants or provides the target.

Examples

Gear Set → Buff

Skill → Buff

Potion → Buff

Example

```
Spell Power Cure

grants

Major Courage
```

---

## applies

The source applies the target.

Usually used for debuffs or status effects.

Example

```
Mind Blast

applies

Leeching Shadow
```

---

## removes

The source removes an existing effect.

Example

```
Purge

removes

Burning
```

---

## scales_with

The source becomes stronger based on the target.

Example

```
Radiating Regeneration

scales_with

Healing Done
```

---

## conflicts_with

The source cannot coexist with the target.

Example

```
Oakensoul Ring

conflicts_with

Weapon Swap
```

---

## synergizes_with

The source works particularly well with the target.

Example

```
Roaring Opportunist

synergizes_with

Jorvuld's Guidance
```

---

# Collection

## drops_from

The source is obtained from the target.

Example

```
Spell Power Cure

drops_from

White-Gold Tower
```

---

## contains

The source contains the target.

Example

```
Cloudrest

contains

Z'Maja
```

---

## rewarded_by

The source is awarded for completing the target.

Example

```
Perfected Bahsei's Mania

rewarded_by

Rockgrove
```

---

## unlocks

Completing the source unlocks the target.

Example

```
Achievement

unlocks

Collectible
```

---

# Organization

## belongs_to

The source belongs to the target.

Examples

Skill → Skill Line

Boss → Trial

Mechanic → Encounter Phase

---

## requires

The source requires the target.

Example

```
Skill Morph

requires

Base Skill
```

---

## has_phase

Used by encounters.

Example

```
Cloudrest

has_phase

Execute Phase
```

---

## uses

The source uses the target.

Examples

Skill → Ultimate

Mechanic → Portal

Boss → Mechanic

---

# Design Rules

Relationship names should:

- Be verbs whenever practical.
- Read naturally.
- Be specific.
- Avoid duplicates.

Prefer

```
grants
```

instead of

```
provides
```

Prefer

```
belongs_to
```

instead of

```
member_of
```

One concept should have one relationship name.

---

Combat
    grants
    applies
    removes
    scales_with
    conflicts_with
    synergizes_with

Structure
    belongs_to
    contains
    has_phase
    requires

Acquisition
    drops_from
    rewarded_by
    unlocks

Reference
    references
    modifies

# Future Relationship Types

Additional relationship types may be added as the Archive expands.

New relationship types should:

- Represent a unique concept.
- Not duplicate existing relationships.
- Be broadly reusable.