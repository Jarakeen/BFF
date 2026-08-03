# Archive Design Principles

**Purpose**

These principles guide the design of the Archive.

The Archive Record Standard defines what a record must contain.

These principles explain why the Archive is organized the way it is.

---

# 1. One Concept, One Record

Every game concept should exist only once in the Archive.

The Archive stores concepts, not implementations.

Example

Spell Power Cure

not

Spell Power Cure Boots

Spell Power Cure Gloves

Spell Power Cure Ring

---

# 2. Facts Over Strategy

The Archive stores objective facts.

Examples

- A buff lasts 20 seconds.
- A boss casts Mind Blast.
- A gear set grants Major Courage.

The Archive does not store opinions or preferred strategies.

Player guidance belongs in guides, not the Archive.

---

# 3. Relationships Over Duplication

Information should be connected rather than repeated.

Instead of storing the same information in multiple records, create a relationship between records.

---

# 4. Preserve Identity

Every Archive Record receives one permanent archive_no.

Archive Numbers never change.

Relationships reference archive_no rather than display names whenever practical.

---

# 5. Builders Have One Job

Builders convert raw source data into Archive Records.

Builders do not perform analysis or recommendations.

---

# 6. Validation Before Publication

Every dataset should be validated before it becomes part of the Archive.

Invalid data should be corrected rather than ignored.

---

# 7. Prefer Simplicity

When multiple designs solve the same problem, prefer the simpler design.

Simple systems are easier to understand, test, and maintain.

---

# 8. Extend, Don't Replace

New entity types should fit within the existing Archive structure whenever possible.

Avoid creating special cases unless they provide significant long-term value.

---

# 9. Human Readable

Archive data should remain understandable without specialized tools.

A developer should be able to open a JSON file and understand what it represents.

---

# 10. Build for Longevity

The Archive should be designed to remain useful over many years.

Adding new data should require extending the Archive rather than redesigning it.