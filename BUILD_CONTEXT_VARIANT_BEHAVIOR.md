# Build Context Variant Behavior

This note documents how Team, Boss, and Team + Boss build variants are interpreted throughout FoundryDock.

## Core rule

A Context Variant is **sparse override data**, not a standalone build.

If a variant contains only a monster-set change, the effective build is the player's full base build with only those specified monster-set slots replaced. Blank or omitted variant fields inherit from the lower-specificity context or the base build. They do **not** mean that the player has no value in that slot.

Example:

- Rik's base build contains his full armor, weapons, jewelry, skills, CP, Mundus, food, and potion.
- A Taleria variant contains only a different Head and Shoulders set.
- The effective Taleria build is Rik's complete base build with those Head and Shoulders values overlaid.
- Coverage, Comp Maker, Optimization, Rotation, and other consumers that request the resolved build must evaluate that complete effective build, not the sparse variant record by itself.

## Resolution model

Context resolution is field-by-field. Matching variants are layered from lower specificity to higher specificity, with the most specific nonblank value winning.

Conceptually:

`Base Build -> Boss wildcard/exact -> Team -> Team + Boss`

The canonical resolver remains `services.build_context_variant_service.resolve_build_context()`; consumers should not reimplement inheritance or treat `BuildContextVariant` as a complete build.

## Field behavior

Sparse inheritance applies to:

- armor slots and their individual nonblank properties;
- front/back weapons and off-hands;
- jewelry;
- Mundus and second Mundus;
- Champion Points;
- front/back skill bars, where only nonblank skill positions replace the inherited slot;
- food;
- potion.

Therefore, a variant showing only one or two changed items in the UI is expected and desirable. The UI is showing the **delta**, while engines should consume the **resolved effective build**.

## Coverage-specific expectation

Team Health Check / Coverage must call the shared build-context resolver for the selected Team/Boss context before auditing capabilities. A sparse variant must never be interpreted as a player wearing only the explicitly listed variant gear.

This distinction is important for raid-lead workflows because Context Variants are intended to describe small encounter-specific changes without cloning a full build for every boss.
